#ifndef CTGP_DIAGNOSTIC_ONLY
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
#include <wups/config/WUPSConfigItemStub.h>
#include <coreinit/filesystem.h>
#include <content_redirection/redirection.h>
#include <coreinit/cache.h>
#include <coreinit/memorymap.h>
#include <coreinit/title.h>
#include <coreinit/dynload.h>
#if defined(CTGP_PREFLIGHT_ONLY) || defined(CTGP_CRASH_CAPTURE)
#include <coreinit/exception.h>
#include <coreinit/debug.h>
#endif
#include <notifications/notifications.h>

#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include "dlc_fs.h"

WUPS_PLUGIN_NAME("CTGP-Cafe Loader");
WUPS_PLUGIN_DESCRIPTION("Custom tracks for Mario Kart 8: patches the game at boot and loads the CTGP-Cafe content");
#ifdef CTGP_PREFLIGHT_ONLY
WUPS_PLUGIN_VERSION("v0.14-preflight");
#elif defined(CTGP_CRASH_CAPTURE)
WUPS_PLUGIN_VERSION("v0.29-protarium-ww");
#else
WUPS_PLUGIN_VERSION("v0.13-dynamic-kernel");
#endif
WUPS_PLUGIN_AUTHOR("KatsuMaki1");
WUPS_PLUGIN_LICENSE("MIT");
// Native FS only: the diagnostic builds confirmed this works inside MK8.

#define SD "/vol/external01"
alignas(64) static FSClient g_client;
alignas(64) static FSCmdBlock g_command;
alignas(64) static FSStat g_stat;
alignas(64) static uint8_t g_io[65536];
alignas(64) static char g_logBuffer[256];
static bool g_fsReady;
using KernelCopyFunction=void (*)(uint32_t,uint32_t,uint32_t);
static KernelCopyFunction g_kernelCopy;
static char g_stage[160]="MK8 not launched";

static char g_last[200];       // last log line (shown by the optional on-screen toast)
static bool g_notifReady;
static bool g_logFile = true;  // Diagnostic logging does not require an empty flag file.
static int g_logErrno;

static void ctLog(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(g_last, sizeof g_last, fmt, ap);
    va_end(ap);
    if (g_logFile && g_fsReady) {
        FSFileHandle file;
        FSInitCmdBlock(&g_command);
        auto opened=FSOpenFile(&g_client,&g_command,SD "/ctgp-loader.txt","a",&file,FS_ERROR_FLAG_ALL);
        g_logErrno=int(opened);
        if(opened>=0) {
            snprintf(g_logBuffer,sizeof g_logBuffer,"%s\n",g_last);
            FSInitCmdBlock(&g_command);
            auto written=FSWriteFile(&g_client,&g_command,(uint8_t*)g_logBuffer,1,strlen(g_logBuffer),file,0,FS_ERROR_FLAG_ALL);
            g_logErrno=written==int(strlen(g_logBuffer))?0:-1;
            FSInitCmdBlock(&g_command);
            auto closed=FSCloseFile(&g_client,&g_command,file,FS_ERROR_FLAG_ALL);
            if(closed<0)g_logErrno=int(closed);
        }
    }
}
#define LOG(FMT, ARGS...) ctLog(FMT, ##ARGS)

#if defined(CTGP_PREFLIGHT_ONLY) || defined(CTGP_CRASH_CAPTURE)
void on_app_starting();
static char g_crashText[1800];
static OSExceptionCallbackFn g_previous[3];
static bool g_handlersInstalled;
static const OSExceptionType g_exceptions[]={OS_EXCEPTION_TYPE_DSI,OS_EXCEPTION_TYPE_ISI,OS_EXCEPTION_TYPE_PROGRAM};
static char *crashText(char *out,const char *text,uint32_t max=160) {
    while(*text && max--)*out++=*text++;
    return out;
}
static char *crashHex(char *out,const char *label,uint32_t value) {
    out=crashText(out,label);
    for(int shift=28;shift>=0;shift-=4)*out++="0123456789ABCDEF"[(value>>shift)&15];
    *out++='\n';return out;
}
static bool crashReadable(uint32_t address,uint32_t size) {
    if(!size || address>UINT32_MAX-(size-1))return false;
    for(uint32_t i=0;i<size;i++)if(!OSEffectiveToPhysical(address+i))return false;
    return true;
}
static char *crashPath(char *out,const char *label,uint32_t address) {
    out=crashText(out,label);
    for(unsigned i=0;i<120;i++) {
        if(!crashReadable(address+i,1)) {out=crashText(out," [unmapped]");break;}
        uint8_t c=*(volatile const uint8_t*)(address+i);
        if(!c)break;
        if(c<32 || c>126) {out=crashText(out," [non-text]");break;}
        *out++=char(c);
    }
    *out++='\n';return out;
}
static BOOL showCrash(OSContext *context,const char *kind) {
    // Avoid FS, heap, varargs and symbol lookup inside the exception callback.
#ifdef CTGP_PREFLIGHT_ONLY
    char *out=crashText(g_crashText,"CTGP v0.14 preflight - NO INJECTION\n");
#else
    char *out=crashText(g_crashText,"CTGP v0.28 BCP resource trace\n");
#endif
    out=crashText(out,kind);*out++='\n';
    out=crashHex(out,"PC=",context->srr0);
    out=crashHex(out,"LR=",context->lr);
    out=crashHex(out,"DAR=",context->dar);
    out=crashHex(out,"DSISR=",context->dsisr);
    out=crashHex(out,"HOOK=",uint32_t(&on_app_starting));
    out=crashHex(out,"LOGGER=",uint32_t(&ctLog));
    out=crashHex(out,"R18=",context->gpr[18]);
    out=crashHex(out,"R25=",context->gpr[25]);
    out=crashHex(out,"R28=",context->gpr[28]);
    if(context->srr0==0x0E9E3E4C) {
        out=crashHex(out,"R3=",context->gpr[3]);out[-1]=' ';
        out=crashHex(out,"Actor=",context->gpr[31]);
        uint32_t actor=context->gpr[31];
        if(actor && crashReadable(actor,8)) {
            out=crashHex(out,"Model=",*(volatile const uint32_t*)actor);out[-1]=' ';
            out=crashHex(out,"Animation=",*(volatile const uint32_t*)(actor+4));
        }
        out=crashText(out,"Course: ");out=crashText(out,g_customFsCourse,150);*out++='\n';
    }
    if(context->srr0==0x0E9D2BC0) {
        out=crashHex(out,"R3=",context->gpr[3]);out[-1]=' ';
        out=crashHex(out,"Actor=",context->gpr[31]);
        uint32_t actor=context->gpr[31];
        if(actor && actor<=UINT32_MAX-0x22C && crashReadable(actor,4) && crashReadable(actor+0x224,8)) {
            out=crashHex(out,"MainModel=",*(volatile const uint32_t*)actor);out[-1]=' ';
            out=crashHex(out,"GateBar=",*(volatile const uint32_t*)(actor+0x224));
        }
        out=crashText(out,"Course: ");out=crashText(out,g_customFsCourse,150);*out++='\n';
        out=crashText(out,"Gate file: ");out=crashText(out,g_customFsTicketGate,150);*out++='\n';
    }
    if(context->srr0==0x0E8C7660) {
        out=crashHex(out,"R3=",context->gpr[3]);out[-1]=' ';
        out=crashHex(out,"R4=",context->gpr[4]);out[-1]=' ';
        out=crashHex(out,"R5=",context->gpr[5]);
        out=crashHex(out,"R6=",context->gpr[6]);out[-1]=' ';
        out=crashHex(out,"R27=",context->gpr[27]);out[-1]=' ';
        out=crashHex(out,"R30=",context->gpr[30]);
        // The verified v81 caller uses this course-heap holder. Read only;
        // never call allocator/FS functions from an exception callback.
        uint32_t holder=context->gpr[27];
        if(holder && holder<=UINT32_MAX-0x3D34 && crashReadable(holder+0x3D1C,0x18)) {
            out=crashHex(out,"CourseHeap=",*(volatile const uint32_t*)(holder+0x3D1C));out[-1]=' ';
            out=crashHex(out,"CourseResource=",*(volatile const uint32_t*)(holder+0x3D28));
        }
    }
    uint32_t frame=context->gpr[1];
    for(unsigned i=0;i<8;i++) {
        if(!crashReadable(frame,4))break;
        uint32_t previous=*(volatile const uint32_t*)frame;
        if(previous<=frame || previous-frame>0x100000 || previous>UINT32_MAX-8 || !crashReadable(previous,8))break;
        char label[]="CALL0=";label[4]=char('0'+i);
        out=crashHex(out,label,*(volatile const uint32_t*)(previous+4));
        frame=previous;
    }
    // This exact v81 resource-loader frame stores its SafeString path at SP+14C.
    // Do not interpret arbitrary exception frames using this layout.
    if(context->srr0==0x0E665F20 && context->gpr[1]<=UINT32_MAX-0x14C) {
        uint32_t slot=context->gpr[1]+0x14C;
        if(crashReadable(slot,4)) {
            uint32_t path=*(volatile const uint32_t*)slot;
            out=crashHex(out,"PATHPTR=",path);
            out=crashPath(out,"Path: ",path);
        }
        out=crashPath(out,"Name: ",context->gpr[25]);
    }
    out=crashHex(out,"FS redirects=",g_customFsRedirects);out[-1]=' ';
    out=crashHex(out,"FS status=",uint32_t(g_customFsStatus));
    out=crashText(out,"FS last: ");out=crashText(out,g_customFsLast,150);*out++='\n';
    out=crashText(out,"FS failed: ");out=crashText(out,g_customFsFailed,150);*out++='\n';
    out=crashText(out,"Stage: ");out=crashText(out,g_stage);*out++='\n';
    out=crashText(out,"Last: ");out=crashText(out,g_last);*out=0;
    OSFatal(g_crashText);
    return FALSE;
}
static BOOL onDSI(OSContext *c){return showCrash(c,"DSI");}
static BOOL onISI(OSContext *c){return showCrash(c,"ISI");}
static BOOL onProgram(OSContext *c){return showCrash(c,"PROGRAM");}
static void installHandlers() {
    OSExceptionCallbackFn callbacks[]={onDSI,onISI,onProgram};
    for(unsigned i=0;i<3;i++)g_previous[i]=OSSetExceptionCallbackEx(OS_EXCEPTION_MODE_GLOBAL_ALL_CORES,g_exceptions[i],callbacks[i]);
    g_handlersInstalled=true;
}
static void restoreHandlers() {
    if(!g_handlersInstalled)return;
    for(unsigned i=0;i<3;i++)OSSetExceptionCallbackEx(OS_EXCEPTION_MODE_GLOBAL_ALL_CORES,g_exceptions[i],g_previous[i]);
    g_handlersInstalled=false;
}
#endif

static void toast(bool error, const char *text) {
    if (!g_notifReady) return;
    char buf[220];
    snprintf(buf, sizeof buf, "CTGP: %s", text);
    if (error) NotificationModule_AddErrorNotification(buf); else NotificationModule_AddInfoNotification(buf);
}

// MK8 title IDs: EB00 = JPN, EC00 = USA, ED00 = EUR.
static const uint64_t MK8_TIDS[] = {0x000500001010EB00ull, 0x000500001010EC00ull, 0x000500001010ED00ull};

// One layer per pack directory (skip_<name> disables it) instead of merging all of /vol/content.
static const char *PACK_DIRS[] = {"course", "mapobj", "ui", "custom", "charger", "audio", "common", "driver", "kart",
                                "driver_anim", "driver_tex", "race_common", "ui3d", "trophy", "ghost", "data"};
// Only base content layers; AOC ownership/detection remains native.
static CRLayerHandle g_layers[sizeof(PACK_DIRS)/sizeof(PACK_DIRS[0])+1];
static int g_numLayers;
static bool g_crReady;
static int g_ioStatus;

static bool exists(const char *path) {
    if(!g_fsReady)return false;
    FSInitCmdBlock(&g_command);
    g_ioStatus=int(FSGetStat(&g_client,&g_command,path,&g_stat,FS_ERROR_FLAG_ALL));
    return g_ioStatus>=0;
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
    LOG("reading %s",path);
    if(!exists(path) || (g_stat.flags&FS_STAT_DIRECTORY) || !g_stat.size || g_stat.size>2*1024*1024)return false;
    uint32_t size=g_stat.size;
    FSFileHandle file;
    FSInitCmdBlock(&g_command);
    g_ioStatus=int(FSOpenFile(&g_client,&g_command,path,"r",&file,FS_ERROR_FLAG_ALL));
    if(g_ioStatus<0) {LOG("open failed=%d",g_ioStatus);return false;}
    out.resize(size);
    uint32_t pos=0;
    while(pos<size) {
        uint32_t chunk=size-pos;if(chunk>sizeof g_io)chunk=sizeof g_io;
        FSInitCmdBlock(&g_command);
        auto bytes=FSReadFile(&g_client,&g_command,g_io,1,chunk,file,0,FS_ERROR_FLAG_ALL);
        g_ioStatus=int(bytes);
        if(bytes<=0 || uint32_t(bytes)>chunk)break;
        memcpy(out.data()+pos,g_io,bytes);pos+=bytes;
    }
    bool ok=pos==size;
    FSInitCmdBlock(&g_command);FSCloseFile(&g_client,&g_command,file,FS_ERROR_FLAG_ALL);
    LOG("read %u/%u bytes",pos,size);
    return ok;
}

static bool mappedRange(uint32_t at,uint32_t len) {
    if(!len || at>UINT32_MAX-(len-1))return false;
    uint32_t last=at+len-1;
    if(!OSEffectiveToPhysical(at) || !OSEffectiveToPhysical(last))return false;
    for(uint32_t page=at&~0xFFFu;page<(last&~0xFFFu);) {
        page+=0x1000;if(!OSEffectiveToPhysical(page))return false;
    }
    return true;
}

// Copy `len` bytes over game memory, bypassing page protection. `src` must be 4-aligned heap memory.
static bool poke(uint32_t dst, const void *src, uint32_t len) {
    if(!g_kernelCopy) {LOG("kernel copy export unavailable; no write");return false;}
    uint32_t source=uint32_t(src);
    if(!mappedRange(dst,len) || !mappedRange(source,len)) { LOG("no physical mapping for %08X",dst);return false; }
    // KernelCopyData bypasses the data cache. Flush destination first so no dirty
    // neighbouring bytes survive the physical copy, and publish the source.
    // Use dcbf-based FlushRange afterwards, as in the original CafeLoader:
    // dcbi-based InvalidateRange faults on the game's read-only executable pages.
    DCFlushRange((void *) dst, len);
    DCFlushRange((void *) src, len);
    for(uint32_t offset=0;offset<len;) {
        uint32_t chunk=len-offset;
        uint32_t destLeft=0x1000-((dst+offset)&0xFFF),srcLeft=0x1000-((source+offset)&0xFFF);
        if(chunk>destLeft)chunk=destLeft;
        if(chunk>srcLeft)chunk=srcLeft;
        g_kernelCopy(OSEffectiveToPhysical(dst+offset),OSEffectiveToPhysical(source+offset),chunk);
        offset+=chunk;
    }
    DCFlushRange((void *)dst,len);
    ICInvalidateRange((void *) dst, len);
    if(memcmp((const void*)dst,src,len)!=0) {LOG("copy readback failed at %08X",dst);return false;}
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
    return p==hax.size();
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
    if(data.size()<0x17E8 || memcmp(data.data()+0x17DC,"custom/cup0",12)) {
        LOG("pack requires private CUP0 path; install matching Data.bin");return false;
    }

    // Refuse to touch a game build the pack was not made for: every patched address must hold its original bytes.
    LOG("verifying game bytes");
    bool match = forEachHax(verify, [](uint32_t at, const uint8_t *orig, uint32_t len) {
        if (!mappedRange(at,len) || memcmp((const void *) at, orig, len) != 0) {
            LOG("game verification failed at %08X; not patching", at);
            return false;
        }
        return true;
    });
    if (!match) return false;
    LOG("game byte verification passed");

    uint32_t textBase = be32(&addr[0]), dataBase = be32(&addr[4]);
    if(addr.size()!=8 || textBase!=0x0F800000 || dataBase!=0x10400020 || code.size()>0x200000 || data.size()>0x100000 || code.size()<4 || (code.size()&3) || be32(code.data()+code.size()-4)!=0x4E800020) {
        LOG("unsupported pack destination or missing log stub");return false;
    }
    code.resize((code.size()+3)&~3u);data.resize((data.size()+3)&~3u);
    // Require an exact verification entry for every patch before writing anything.
    bool coverage=forEachHax(patches,[&](uint32_t at,const uint8_t*,uint32_t len) {
        bool found=false;
        bool valid=forEachHax(verify,[&](uint32_t check,const uint8_t*,uint32_t size) {if(check==at && size==len)found=true;return true;});
        return valid && found && mappedRange(at,len);
    });
    if(!mappedRange(textBase,code.size()) || !mappedRange(dataBase-4,data.size()+4) || !coverage) {
        LOG("pack range validation failed");return false;
    }
    // Fixed original CTGP blob addresses: refuse to overwrite existing nonzero data.
#ifdef CTGP_PREFLIGHT_ONLY
    LOG("preflight PASS: pack read, bytes and ranges checked; NO writes or layers");
    return true;
#endif
    LOG("checking empty code destination %08X size=%u",textBase,unsigned(code.size()));
    snprintf(g_stage,sizeof g_stage,"Inspecting code destination");
    for(uint32_t i=0;i<code.size();i++)if(*(volatile uint8_t*)(textBase+i)) {LOG("code destination occupied at %08X",textBase+i);return false;}
    LOG("checking empty data destination %08X size=%u",dataBase-4,unsigned(data.size()+4));
    snprintf(g_stage,sizeof g_stage,"Inspecting data destination");
    for(uint32_t i=0;i<data.size()+4;i++)if(*(volatile uint8_t*)(dataBase-4+i)) {LOG("data destination occupied at %08X",dataBase-4+i);return false;}
    snprintf(g_stage,sizeof g_stage,"Copying CTGP code/data");
    LOG("preflight passed; copying code/data");
    LOG("code %zu bytes -> %08X, data %zu bytes -> %08X", code.size(), textBase, data.size(), dataBase);
    if (!poke(textBase, code.data(), code.size())) return false;
    LOG("code copy readback passed; copying data");
    if (!poke(dataBase, data.data(), data.size())) return false;
    LOG("data copy readback passed; installing log stub pointer");

    // The console loader stored its log function at dataBase-4 and the code calls it blindly: use the `blr` stub that ends Code.bin.
    std::vector<uint32_t> logPtr(1, textBase + (uint32_t) code.size() - 4);
    if (!poke(dataBase - 4, logPtr.data(), 4)) return false;

    uint32_t applied = 0;
    snprintf(g_stage,sizeof g_stage,"Applying verified CTGP hooks");
    bool ok = forEachHax(patches, [&](uint32_t at, const uint8_t *bytes, uint32_t len) {
        LOG("patch %u at %08X len=%u",applied,at,len);
        std::vector<uint32_t> tmp((len + 3) / 4);          // poke() needs an aligned source
        memcpy(tmp.data(), bytes, len);
        if (!poke(at, tmp.data(), len)) return false;
        applied++;
        return true;
    });
    LOG("patches applied: %u", applied);
    if(!ok) {
        bool restored=forEachHax(verify,[](uint32_t at,const uint8_t* bytes,uint32_t len) {
            std::vector<uint32_t> tmp((len+3)/4);memcpy(tmp.data(),bytes,len);
            return poke(at,tmp.data(),len);
        });
        LOG("patch copy failed; original hooks restored=%d",restored);
    }
    return ok;
}

static void removeLayers() {
    for (int i = 0; i < g_numLayers; i++) ContentRedirection_RemoveFSLayer(g_layers[i]);
    g_numLayers = 0;
}

static void addLayers(const char *content) {
    // Do not overlay the AOC mount: v0.22 regressed owned-DLC detection.
    char target[64],repl[160],skip[40];
    for(const char *name:PACK_DIRS) {
        snprintf(skip,sizeof skip,"skip_%s",name);
        if(flag(skip)){LOG("layer %s skipped",name);continue;}
        snprintf(target,sizeof target,"/vol/content/%s",name);
        snprintf(repl,sizeof repl,"%s/%s",content,name);
        if(!exists(repl) || !(g_stat.flags&FS_STAT_DIRECTORY))continue;
        snprintf(repl,sizeof repl,"fs:%s/%s",content,name);
        ContentRedirectionStatus st=ContentRedirection_AddFSLayerEx(&g_layers[g_numLayers],name,target,repl,FS_LAYER_TYPE_EX_MERGE_DIRECTORY);
        LOG("layer %s target=%s: %s",name,target,ContentRedirection_GetStatusStr(st));
        if(st==CONTENT_REDIRECTION_RESULT_SUCCESS)g_numLayers++;
    }
    // CUP0 stays private; no root layer or DLC mount is added.
}

static bool checkCup0(const char *content) {
    std::vector<uint8_t> source,redirected;
    char path[160];snprintf(path,sizeof path,"%s/data.cup0",content);
    if(!readFile(path,source)) {LOG("CUP0 SD read failed status=%d",g_ioStatus);return false;}
    if(source.size()<12 || memcmp(source.data(),"CUP0",4) || be32(source.data()+4)>256 || be32(source.data()+8)!=12+80*be32(source.data()+4) || be32(source.data()+8)>=source.size()) {
        LOG("CUP0 SD invalid header/size=%u",unsigned(source.size()));return false;
    }
    LOG("CUP0 SD size=%u cups=%u; probing game path",unsigned(source.size()),be32(source.data()+4));
    if(!readFile("/vol/content/custom/cup0",redirected)) {
        LOG("CUP0 game-path read failed status=%d; SD file readable",g_ioStatus);return false;
    }
    if(source!=redirected) {LOG("CUP0 game-path differs from SD: SD=%u game=%u",unsigned(source.size()),unsigned(redirected.size()));return false;}
    LOG("CUP0 game-path read matches SD: %u bytes",unsigned(source.size()));return true;
}

INITIALIZE_PLUGIN() {
#ifdef CTGP_PREFLIGHT_ONLY
    WUPSConfigAPIOptionsV1 options={.name="CTGP preflight v0.14"};
#elif defined(CTGP_CRASH_CAPTURE)
    WUPSConfigAPIOptionsV1 options={.name="CTGP loader v0.20"};
#else
    WUPSConfigAPIOptionsV1 options={.name="CTGP loader v0.13"};
#endif
    WUPSConfigAPI_Init(options,[](WUPSConfigCategoryHandle root) {
        WUPSConfigItemStub_AddToCategory(root,g_stage);
        WUPSConfigItemStub_AddToCategory(root,g_last);
        return WUPSCONFIG_API_CALLBACK_RESULT_SUCCESS;
    },[](){});
    // Keep initialization free of logging backends and content module calls.
    // Initialize content redirection inside MK8, after the native SD journal opens.
}

DEINITIALIZE_PLUGIN() {
#if defined(CTGP_PREFLIGHT_ONLY) || defined(CTGP_CRASH_CAPTURE)
    restoreHandlers();
#endif
    removeLayers();
    if (g_crReady) ContentRedirection_DeInitLibrary();
    if (g_notifReady) NotificationModule_DeInitLibrary();
}

ON_APPLICATION_START() {
    resetCustomFs();
    // Log before filtering: a forwarder/repacked title must not fail silently.
    // No code or content modification is allowed outside the supported MK8 IDs.
    uint64_t tid = OSGetTitleID();
    if(!isMK8(tid))return;
#if defined(CTGP_PREFLIGHT_ONLY) || defined(CTGP_CRASH_CAPTURE)
    installHandlers();
    snprintf(g_stage,sizeof g_stage,"Handlers installed; starting native FS");
#endif
    FSInit();
    auto added=FSAddClient(&g_client,FS_ERROR_FLAG_ALL);
    if(added<0) {snprintf(g_stage,sizeof g_stage,"FSAddClient=%d",int(added));return;}
    g_fsReady=true;
    struct CloseFS {~CloseFS(){FSDelClient(&g_client,FS_ERROR_FLAG_ALL);g_fsReady=false;}} closeFS;
    snprintf(g_stage,sizeof g_stage,"Reading SD pack with native FS");
    g_logFile = true;
#ifdef CTGP_PREFLIGHT_ONLY
    LOG("v0.14 PREFLIGHT ONLY app start, title %016llX",tid);
#elif defined(CTGP_CRASH_CAPTURE)
    LOG("v0.20 resource trace app start, title %016llX",tid);
#else
    LOG("v0.13 dynamic kernel app start, title %016llX", tid);
#endif
    if(g_logErrno) {
        snprintf(g_stage,sizeof g_stage,"Journal open/write/close failed=%d; loader skipped",g_logErrno);
        return;
    }
    LOG("initializing ContentRedirection");
    g_crReady = ContentRedirection_InitLibrary() == CONTENT_REDIRECTION_RESULT_SUCCESS;
    LOG("ContentRedirection ready=%d",g_crReady);
    g_notifReady = NotificationModule_InitLibrary() == NOTIFICATION_MODULE_RESULT_SUCCESS;
    if (g_logErrno) {
        char problem[160];
        snprintf(problem,sizeof problem,"SD log unavailable (status %d): /ctgp-loader.txt",g_logErrno);
        toast(true,problem);
    }

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
#ifdef CTGP_PREFLIGHT_ONLY
    noContent=true;noCode=false;
#endif
    LOG("switches no_code=%d no_content=%d; ContentRedirection=%d",noCode,noContent,g_crReady);
    LOG("pack=%s content=%s", dir[0] ? dir : "(none)", content[0] ? content : "(none)");
    if (!noContent && content[0] && !g_crReady) {
        LOG("ContentRedirection unavailable; refusing to enable code without its content");
        toast(true,g_last);return;
    }
    if (noCode || !dir[0]) {
        if (g_crReady && !noContent && content[0]) addLayers(content);
        toast(false, "content only"); return;
    }

    // Match the successful v0.12 probe: no direct homebrew_kernel import.
    // Find an already-loaded module; do not load a missing one or hardcode a pointer.
    LOG("resolving kernel module/export dynamically");
    OSDynLoad_Module kernel=0;
    auto loaded=OSDynLoad_IsModuleLoaded("homebrew_kernel",&kernel);
    void *copy=nullptr;
    auto found=loaded;
    if(loaded==OS_DYNLOAD_OK)
        found=OSDynLoad_FindExport(kernel,OS_DYNLOAD_EXPORT_FUNC,"KernelCopyData",&copy);
    if(loaded!=OS_DYNLOAD_OK || found!=OS_DYNLOAD_OK || !copy) {
        LOG("kernel lookup failed: loaded=%08X export=%08X",unsigned(loaded),unsigned(found));
        snprintf(g_stage,sizeof g_stage,"Kernel unavailable; no injection");toast(true,g_last);return;
    }
    g_kernelCopy=reinterpret_cast<KernelCopyFunction>(copy);
    LOG("kernel export resolved at %08X",unsigned(uintptr_t(copy)));

#ifndef CTGP_PREFLIGHT_ONLY
    if(noContent || !content[0]) {
        snprintf(g_stage,sizeof g_stage,"No CTGP content; injection skipped");
        LOG("refusing code without content for required data.cup0");return;
    }
    snprintf(g_stage,sizeof g_stage,"Checking redirected data.cup0 before injection");
    addLayers(content);
    if(!checkCup0(content)) {
        snprintf(g_stage,sizeof g_stage,"CUP0 check failed; NO injection, vanilla");
        toast(true,g_last);removeLayers();return;
    }
#endif
    if (loadCode(dir)) {
#ifdef CTGP_PREFLIGHT_ONLY
        snprintf(g_stage,sizeof g_stage,"Preflight passed; NO injection or layers");
        toast(false,g_stage);
        return;
#endif
        g_customFsReady=true;
        LOG("all code copies verified; content layers already checked; targeted FS routing enabled");
        LOG("CTGP-Cafe code loaded"); toast(false, "code loaded");
        snprintf(g_stage,sizeof g_stage,"CTGP loaded; content layers=%d",g_numLayers);
    }
    else { char why[200]; snprintf(why, sizeof why, "%s", g_last); snprintf(g_stage,sizeof g_stage,"CTGP refused; see reason below"); LOG("CTGP-Cafe code NOT loaded: %s",why); toast(true, why); removeLayers(); }
}

ON_APPLICATION_ENDS() {
    g_customFsReady=false;
#if defined(CTGP_PREFLIGHT_ONLY) || defined(CTGP_CRASH_CAPTURE)
    restoreHandlers();
#endif
    g_kernelCopy=nullptr;
    removeLayers();
    if (g_notifReady) { NotificationModule_DeInitLibrary(); g_notifReady = false; }
}
#endif
