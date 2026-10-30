/* Behavioral tests for the actual native C wrappers with fake game services.
 * Run with a host C compiler. Does not execute or claim to emulate MK8.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned char memory[0x2000000];
static unsigned int *word(unsigned int address) {
    return (unsigned int *)(memory + (address & 0x1ffffff));
}
static unsigned char *byte_at(unsigned int address) {
    return memory + (address & 0x1ffffff);
}
static void *resolve(unsigned int address);
#define W(p, o) (*word((unsigned int)(p) + (o)))
#define B(p, o) (*byte_at((unsigned int)(p) + (o)))
#define FN(address, type) ((type)resolve(address))
#include "../tools/native/costume_selector.c"

#define CHECK(condition) do { if (!(condition)) { \
    fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #condition); exit(1); } } while (0)
static unsigned calls_main, calls_list, calls_grid, calls_apply, calls_cell;
static unsigned applied_player, applied_character, applied_variant, transitions, preview_calls;
static unsigned texture_calls, texture_character;
static const u16 *last_name;

void original_main_event(u32 p, u32 e) { (void)p; (void)e; calls_main++; }
void original_list_event(u32 p, u32 e) {
    calls_list++;
    if (!W(e, 8)) B(p, 0x190) = 1;
}
void original_apply(u32 p, const u32 *c) { (void)p; (void)c; calls_apply++; }
void original_grid(u32 c) {
    calls_grid++; W(c,0x5c)=3; W(c,0x60)=3; W(c,0x64)=0x70000;
    for (u32 i=0;i<9;i++) { B(0x70000+i*16,8)=1; W(0x70000+i*16,12)=(i%3)*3+i/3; }
}
void original_cell(u32 c) {
    calls_cell++;
    CHECK(W(c, 0xac) == 4);
    CHECK(W(W(c, 0x5c), 0x0c) == 0);
}
void original_setup(u32 c, const u32 *m, u32 f, u32 w, u32 p) {
    (void)f; (void)w; (void)p;
    CHECK(*m == 4);
    W(c, 0x268) = *m;
    costume_grid(c);
}
static void classify(u32 p, u32 *out, const u32 *c) { (void)p; CHECK(*c == 0 || *c == 9); *out = 5; }
static u32 get_list(u32 p, u32 player) { (void)p; return 0x20000 + player * 0x1000; }
static void transition(u32 p, u32 state) { (void)p; (void)state; transitions++; }
static u32 get_player(u32 context) { CHECK(context >= 0x60000); return (context - 0x60000) / 0x100 + 8; }
static void set_player(u32 p, const u32 *c, u32 variant, u32 unused) {
    CHECK(unused == 0); applied_player = p; applied_character = *c; applied_variant = variant;
}
static void name(u32 parent, u32 player, const u16 *text) {
    CHECK(parent == 0x10000 && player < 4); last_name = text;
}
static void two_cells(u32 c) {
    CHECK(W(c, 0x268) == COSTUME_MODE);
    W(c, 0x5c) = 3; W(c, 0x60) = 3; W(c, 0x64) = 0x70000;
    B(0x70000, 8) = 1; W(0x70000, 0x0c) = 0;
    B(0x70010, 8) = 1; W(0x70010, 0x0c) = 1;
}
static void move_cursor(u32 c, const u32 *pair) { CHECK((size_t)pair == c + 0x288); }
static u32 get_texture(u32 heap, const u32 *type, const u32 *character, u32 variant) {
    CHECK(heap == 0x5198 && *type == 0 && variant == 0);
    texture_character = *character; return 0xabcdef;
}
static void set_texture(u32 c, u32 pane, u32 texture, u32 kind) {
    (void)c; CHECK(pane == 0x888 && texture == 0xabcdef && kind == 0); texture_calls++;
}
static void reload(u32 object) { CHECK(object == 0x999); preview_calls++; }
static void sound(const char *s, u32 p) { CHECK((size_t)s == 0x100de710 && p < 4); }

static void resize_grid(u32 c,u32 w,u32 h) { CHECK(w==3 && h==1); (void)c; }
static void restore_cursor(u32 c) { (void)c; }
static u32 resource_icon(u32 r,const struct NativeString *path) {
    CHECK(r==0x1234); CHECK(path->vtable==0x100d25d0);
    CHECK(strstr(path->text,"FunkyKong") || strstr(path->text,"Snorlax")); return 0xabcdef;
}
static void *resolve(unsigned int address) {
    switch (address) {
    case 0x0258f88c: return resize_grid;
    case 0x025a086c: return restore_cursor;
    case 0x0253d47c: return resource_icon;
    case 0x025d6470: return classify;
    case 0x025d25dc: return get_list;
    case 0x0253f048: return transition;
    case 0x02563a44: return get_player;
    case 0x0256684c: return set_player;
    case 0x025d25b0: return name;
    case 0x025a0be8: return two_cells;
    case 0x0258fbc4: return move_cursor;
    case 0x0255afb4: return get_texture;
    case 0x02531c54: return set_texture;
    case 0x0219bc6c: return reload;
    case 0x0204886c: return sound;
    default: fprintf(stderr, "Unexpected game service %08x\n", address); exit(1);
    }
}

int main(void) {
    const u32 page = 0x10000, event = 0x15000, control = 0x30000;
    W(0x1018a18c, 0) = 0x1000;
    W(0x1000, 0x14) = 0x2000;
    W(0x1000, 0x0c) = 0x3000;
    W(0x3000, 0) = 4; W(0x3000, 4) = 0x4000; W(0x4000, 12) = 0x5000;
    for (unsigned i = 0; i < 4; i++) W(0x2000, i * 4) = 0x60000 + i * 0x100;
    W(page, 4) = 37; W(page, 0x2fc) = 0x18000; W(0x18000, 0xf8) = 0;
    W(event, 8) = 1; W(event, 0x14) = 2; W(event, 0x18) = 0;
    costume_main_event(page, event);
    CHECK(calls_main == 1 && transitions == 1 && W(0x20000, 0x170) == COSTUME_MODE);
    CHECK(chosen[0][0] == 0 && lists[0] == 0x20000);
    W(page, 4) = 55;
    costume_main_event(page, event);
    CHECK(calls_main == 2 && transitions == 1); /* Native online page is delegated. */
    W(page, 4) = 37;
    W(0x18000, 0xf8) = 1;
    costume_main_event(page, event);
    CHECK(calls_main == 3 && transitions == 1); /* Luigi is delegated. */
    W(0x18000, 0xf8) = 0;
    W(event, 0x18) = 1;
    costume_main_event(page, event);
    CHECK(lists[1] == 0x21000 && W(0x21000, 0x170) == COSTUME_MODE);

    u32 mode = COSTUME_MODE;
    W(0x20000, 0xcc) = page; W(0x20000, 0xd4) = 0; W(0x20000, 0xc8) = control;
    costume_setup(control, &mode, 1, 0, 0);
    CHECK(W(control, 0x268) == COSTUME_MODE && initializing_control == 0);
    CHECK(last_name == mario_name);
    W(control, 0x288) = 1; W(control, 0x28c) = 0;
    W(event, 0x0c) = 0; W(event, 0x14) = 2;
    costume_list_event(0x20000, event);
    CHECK(last_name == sunshine_name && chosen[0][0] == 0); /* Hover does not commit. */
    W(event, 8) = 0;
    costume_list_event(0x20000, event);
    CHECK(calls_list == 1 && chosen[0][0] == 0 && B(0x20000, 0x190) == 1);
    W(event, 8) = 1; W(event, 0x14) = 7;
    costume_list_event(0x20000, event);
    CHECK(chosen[0][0] == 1 && chosen[0][1] == 0);
    CHECK(applied_player == 8 && applied_character == 0 && applied_variant == 1);
    CHECK(W(0x20000, 0x80) == 0x19);
    u32 mario = 0, luigi = 1;
    costume_apply(1, &mario);
    CHECK(applied_player == 9 && applied_variant == 0);
    costume_apply(1, &luigi); CHECK(calls_apply == 1);
    W(control, 0x288) = 99;
    costume_list_event(0x20000, event); CHECK(chosen[0][0] == 1);
    costume_setup(control, &mode, 1, 0, 0);
    CHECK(W(control, 0x288) == 1 && W(control, 0x2b8) == 1);

    const u32 cell = 0x80000;
    W(cell, 0xac) = COSTUME_MODE; W(cell, 0x5c) = 0x70010; W(cell, 0xb4) = 0x888;
    costume_cell(cell);
    CHECK(calls_cell == 1 && texture_calls == 1 && texture_character == 0);
    CHECK(W(cell, 0xac) == COSTUME_MODE && W(0x70010, 0x0c) == 1);
    W(0x10188538, 0) = 0x90000;
    W(0x90000, 0x34) = 4; W(0x90000, 0x38) = 0x91000; W(0x91000, 0) = 0x92000;
    W(0x92000, 0x18) = 0x999;
    reload_preview(0);
    CHECK(preview_calls == 1 && B(0x92000, 0x298) == 1 && B(0x92000, 0x2a9) == 0);
    W(event,0x18)=0; W(event,0x14)=2; W(0x18000,0xf8)=9;
    costume_main_event(page,event);
    CHECK(W(0x20000,0x170)==7);
    mode=7; costume_setup(control,&mode,1,0,0);
    CHECK(last_name==dk_name && calls_grid==1);
    for(u32 i=0;i<9;i++) CHECK(B(0x70000+i*16,8)==(i<3));
    CHECK(W(0x70010,12)==1 && W(0x70020,12)==2);
    W(control,0x288)=2; W(control,0x28c)=0; W(event,0x14)=7;
    costume_list_event(0x20000,event);
    CHECK(chosen[1][0]==2 && chosen[0][0]==1);
    CHECK(applied_character==9 && applied_variant==2 && last_name==snorlax_name);
    W(0x3000,0)=5; W(0x4000,16)=0x5500; W(0x5500,4)=0x1234;
    W(cell,0xac)=7;
    for(u32 i=1;i<3;i++) { W(cell,0x5c)=0x70000+i*16; costume_cell(cell); }
    CHECK(texture_calls==3);
    puts("PASS: DK grid, variant confirmation, group independence, both custom icons");
    puts("PASS: local Mario submenu, delegation, two players, hover/cancel/confirm, cursor bounds, remembered choice, Mario cell texture, preview request");
    return 0;
}
