// CTGP-Cafe loader for Aroma (WUPS): Mario Kart 8 custom tracks.
//
// At the start of Mario Kart 8 (any region) it
//   1. merges the CTGP-Cafe content (courses, UI layouts, data.cup0, ...) over the game's /vol/content, and
//   2. patches the running game: copies the CTGP code/data blob into memory and applies the patch list,
//      after checking that every patched address still holds the original bytes of the build the pack was made for.
//
// SD layout (same as the original CTGP-Cafe release, plus Verify.hax):
//   sd:/cafeloader/<TitleID>/{Addr.bin,Code.bin,Data.bin,Patches.hax,Verify.hax}   code pack for one game build
//   sd:/cafeloader/vol/<TitleID>/content/...                                        courses, ui/cmn/ctgp.szs, data.cup0, ...
// Switches (empty files in sd:/wiiu/mk8-ct/): log_file, notif, no_code, no_content, skip_<dir>.
#include <wups.h>
#include <content_redirection/redirection.h>
#include <coreinit/cache.h>
#include <coreinit/memorymap.h>
#include <coreinit/title.h>
#include <kernel/kernel.h>
#include <notifications/notifications.h>
#include <sys/stat.h>
#include <whb/log.h>
#include <whb/log_cafe.h>
#include <whb/log_module.h>
#include <whb/log_udp.h>

#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

WUPS_PLUGIN_NAME("CTGP-Cafe Loader");
WUPS_PLUGIN_DESCRIPTION("Custom tracks for Mario Kart 8: patches the game at boot and loads the CTGP-Cafe content");
WUPS_PLUGIN_VERSION("v0.3");
WUPS_PLUGIN_AUTHOR("KatsuMaki1");
WUPS_PLUGIN_LICENSE("MIT");

#define SD "fs:/vol/external01"

static char g_last[200];       // last log line (shown by the optional on-screen toast)
static bool g_notifReady;
static bool g_logFile;         // opt-in: sd:/wiiu/mk8-ct/log_file -> sd:/wiiu/mk8-ct/log.txt

static void ctLog(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(g_last, sizeof g_last, fmt, ap);
    va_end(ap);
    WHBLogPrintf("[ctgp] %s", g_last);
    if (g_logFile) {
        mkdir(SD "/wiiu", 0777);
        mkdir(SD "/wiiu/mk8-ct", 0777);
        if (FILE *f = fopen(SD "/wiiu/mk8-ct/log.txt", "a")) { fprintf(f, "%s\n", g_last); fclose(f); }
    }
}
#define LOG(FMT, ARGS...) ctLog(FMT, ##ARGS)

static void toast(bool error, const char *text) {
    if (!g_notifReady) return;
    char buf[220];
    snprintf(buf, sizeof buf, "CTGP: %s", text);
    if (error) NotificationModule_AddErrorNotification(buf); else NotificationModule_AddInfoNotification(buf);
}

// MK8 title IDs: EB00 = JPN, EC00 = USA, ED00 = EUR.
static const uint64_t MK8_TIDS[] = {0x000500001010EB00ull, 0x000500001010EC00ull, 0x000500001010ED00ull};

// One layer per pack directory (skip_<name> disables it) instead of merging all of /vol/content.
static const char *PACK_DIRS[] = {"course", "mapobj", "ui", "custom", "charger", "audio"};
static CRLayerHandle g_layers[8];
static int g_numLayers;
static bool g_crReady;

static bool exists(const char *path) {
    FILE *f = fopen(path, "rb");
    if (f) fclose(f);
    return f != nullptr;
}

static bool flag(const char *name) {
    char path[128];
    snprintf(path, sizeof path, SD "/wiiu/mk8-ct/%s", name);
    return exists(path);
}

static bool isMK8(uint64_t t) {
    for (auto id : MK8_TIDS) if (id == t) return true;
    return false;
}

static bool readFile(const char *path, std::vector<uint8_t> &out) {
    FILE *f = fopen(path, "rb");
    if (!f) return false;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    out.resize(n > 0 ? n : 0);
    bool ok = n >= 0 && fread(out.data(), 1, n, f) == (size_t) n;
    fclose(f);
    return ok;
}

// Copy `len` bytes over game memory, bypassing page protection. `src` must be 4-aligned heap memory.
static bool poke(uint32_t dst, const void *src, uint32_t len) {
    uint32_t pd = OSEffectiveToPhysical(dst), ps = OSEffectiveToPhysical((uint32_t) src);
    if (!pd || !ps) { LOG("no physical mapping for %08X", dst); return false; }
    KernelCopyData(pd, ps, len);
    DCFlushRange((void *) dst, len);
    ICInvalidateRange((void *) dst, len);
    return true;
}

static uint32_t be32(const uint8_t *p) { return ((uint32_t) p[0] << 24) | (p[1] << 16) | (p[2] << 8) | p[3]; }

// .hax = u16 count, then count * { u16 len, u32 addr, u8 data[len] } (big endian). Calls fn(addr, data, len) for each entry.
template <class F> static bool forEachHax(const std::vector<uint8_t> &hax, F fn) {
    if (hax.size() < 2) return false;
    uint32_t count = (hax[0] << 8) | hax[1], p = 2;
    for (uint32_t i = 0; i < count; i++) {
        if (p + 6 > hax.size()) return false;
        uint32_t len = (hax[p] << 8) | hax[p + 1], addr = be32(&hax[p + 2]);
        p += 6;
        if (p + len > hax.size()) return false;
        if (!fn(addr, &hax[p], len)) return false;
        p += len;
    }
    return true;
}

static bool loadCode(const char *dir) {
    char path[160];
    std::vector<uint8_t> addr, code, data, patches, verify;
    snprintf(path, sizeof path, "%s/Addr.bin", dir);     bool a = readFile(path, addr);
    snprintf(path, sizeof path, "%s/Code.bin", dir);     bool c = readFile(path, code);
    snprintf(path, sizeof path, "%s/Data.bin", dir);     bool d = readFile(path, data);
    snprintf(path, sizeof path, "%s/Patches.hax", dir);  bool h = readFile(path, patches);
    snprintf(path, sizeof path, "%s/Verify.hax", dir);   bool v = readFile(path, verify);
    if (!a || !c || !d || !h || !v || addr.size() < 8) { LOG("incomplete pack in %s (addr=%d code=%d data=%d patches=%d verify=%d)", dir, a, c, d, h, v); return false; }

    // Refuse to touch a game build the pack was not made for: every patched address must hold its original bytes.
    bool match = forEachHax(verify, [](uint32_t at, const uint8_t *orig, uint32_t len) {
        if (memcmp((const void *) at, orig, len) != 0) {
            LOG("game memory at %08X is %08X, pack expects %08X -> wrong game build, not patching", at, be32((const uint8_t *) at), be32(orig));
            return false;
        }
        return true;
    });
    if (!match) return false;

    uint32_t textBase = be32(&addr[0]), dataBase = be32(&addr[4]);
    LOG("code %zu bytes -> %08X, data %zu bytes -> %08X", code.size(), textBase, data.size(), dataBase);
    code.resize((code.size() + 3) & ~3u); data.resize((data.size() + 3) & ~3u);
    if (!poke(textBase, code.data(), code.size()) || !poke(dataBase, data.data(), data.size())) return false;

    // The console loader stored its log function at dataBase-4 and the code calls it blindly: use the `blr` stub that ends Code.bin.
    std::vector<uint32_t> logPtr(1, textBase + (uint32_t) code.size() - 4);
    if (!poke(dataBase - 4, logPtr.data(), 4)) return false;

    uint32_t applied = 0;
    bool ok = forEachHax(patches, [&](uint32_t at, const uint8_t *bytes, uint32_t len) {
        std::vector<uint32_t> tmp((len + 3) / 4);          // poke() needs an aligned source
        memcpy(tmp.data(), bytes, len);
        if (!poke(at, tmp.data(), len)) return false;
        applied++;
        return true;
    });
    LOG("patches applied: %u", applied);
    return ok;
}

static void removeLayers() {
    for (int i = 0; i < g_numLayers; i++) ContentRedirection_RemoveFSLayer(g_layers[i]);
    g_numLayers = 0;
}

static void addLayers(const char *content) {
    char target[64], repl[160], skip[40];
    for (const char *name : PACK_DIRS) {
        snprintf(skip, sizeof skip, "skip_%s", name);
        if (flag(skip)) { LOG("layer %s skipped", name); continue; }
        snprintf(target, sizeof target, "/vol/content/%s", name);
        snprintf(repl, sizeof repl, "%s/%s", content, name);
        ContentRedirectionStatus st = ContentRedirection_AddFSLayerEx(&g_layers[g_numLayers], name, target, repl, FS_LAYER_TYPE_EX_MERGE_DIRECTORY);
        LOG("layer %s: %s", name, ContentRedirection_GetStatusStr(st));
        if (st == CONTENT_REDIRECTION_RESULT_SUCCESS) g_numLayers++;
    }
    if (!flag("skip_cup0")) {
        snprintf(repl, sizeof repl, "%s/data.cup0", content);
        ContentRedirectionStatus st = ContentRedirection_AddFSLayerEx(&g_layers[g_numLayers], "cup0", "/vol/content/data.cup0", repl, FS_LAYER_TYPE_EX_REPLACE_FILE);
        LOG("layer data.cup0: %s", ContentRedirection_GetStatusStr(st));
        if (st == CONTENT_REDIRECTION_RESULT_SUCCESS) g_numLayers++;
    }
}

INITIALIZE_PLUGIN() {
    if (!WHBLogModuleInit()) { WHBLogCafeInit(); WHBLogUdpInit(); }
    g_crReady = ContentRedirection_InitLibrary() == CONTENT_REDIRECTION_RESULT_SUCCESS;
    if (!g_crReady) LOG("ContentRedirectionModule missing");
}

DEINITIALIZE_PLUGIN() {
    removeLayers();
    if (g_crReady) ContentRedirection_DeInitLibrary();
    if (g_notifReady) NotificationModule_DeInitLibrary();
}

ON_APPLICATION_START() {
    // Touch nothing (no log, no SD, no notification) unless this is MK8: this hook also runs for the Wii U menu at boot.
    uint64_t tid = OSGetTitleID();
    if (!isMK8(tid)) return;
    g_logFile = flag("log_file");
    if (flag("notif")) g_notifReady = NotificationModule_InitLibrary() == NOTIFICATION_MODULE_RESULT_SUCCESS;
    LOG("app start, title %016llX", tid);

    // Code pack: this console's region first, then the others. Content folder: first one that holds data.cup0.
    uint64_t order[4] = {tid, MK8_TIDS[2], MK8_TIDS[1], MK8_TIDS[0]};
    char dir[96] = "", content[128] = "";
    for (uint64_t t : order) {
        char p[160];
        if (!dir[0]) {
            snprintf(p, sizeof p, SD "/cafeloader/%016llX/Verify.hax", t);
            if (exists(p)) snprintf(dir, sizeof dir, SD "/cafeloader/%016llX", t);
        }
        if (!content[0]) {
            snprintf(p, sizeof p, SD "/cafeloader/vol/%016llX/content/data.cup0", t);
            if (exists(p)) snprintf(content, sizeof content, SD "/cafeloader/vol/%016llX/content", t);
        }
    }
    if (!dir[0] && !content[0]) { LOG("nothing found in sd:/cafeloader, doing nothing"); toast(true, g_last); return; }

    bool noContent = flag("no_content"), noCode = flag("no_code");
    LOG("pack=%s content=%s", dir[0] ? dir : "(none)", content[0] ? content : "(none)");
    if (g_crReady && !noContent && content[0]) addLayers(content);
    if (noCode || !dir[0]) { toast(false, "content only"); return; }

    if (loadCode(dir)) { LOG("CTGP-Cafe code loaded"); toast(false, "code loaded"); }
    else { char why[200]; snprintf(why, sizeof why, "%s", g_last); LOG("CTGP-Cafe code NOT loaded"); toast(true, why); }
}

ON_APPLICATION_ENDS() {
    removeLayers();
    if (g_notifReady) { NotificationModule_DeInitLibrary(); g_notifReady = false; }
}
