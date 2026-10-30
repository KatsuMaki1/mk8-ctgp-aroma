/* Keep imported Booster cups on their original twelve-button page. */
typedef unsigned int u32;
#ifndef BOOSTER_HOST
#define W(p,o) (*(u32 *)((unsigned char *)(__UINTPTR_TYPE__)(p)+(o)))
#define STR(p) ((const char *)(__UINTPTR_TYPE__)(p))
#endif
#ifndef CUP_STATE
#define CUP_STATE 0x10302564u
#endif
const char booster_marker[]="MK8_BOOSTER_GATE_EUR81_V1";
static u32 last_page;
static u32 selected_icon=0xffffffffu;
volatile u32 booster_allowed;
extern u32 original_gate(u32,u32,u32);

static int invalid(const char *s) {
    static const char name[]="Ginvalid";
    if(!s || s[0]!='G')return 1;
    u32 i=0;
    while(name[i] && s[i]==name[i])i++;
    return !name[i] && !s[i];
}
static int ready(u32 icon) {
    u32 manager=W(CUP_STATE,0);
    if(!manager || W(manager,4)>256 || !W(manager,8))return 0;
    u32 record=W(manager,8);
    for(u32 i=0;i<W(manager,4);i++,record+=0x54) {
        if(W(record,0)!=1 || W(record,4)!=icon)continue;
        for(u32 slot=0;slot<4;slot++) {
            u32 dir=W(record,0x34+4*slot);
            if(!dir || invalid(STR(dir)))return 0;
        }
        return 1;
    }
    return 0;
}
u32 booster_gate(u32 page,u32 extension,u32 event) {
    if(W(extension,0x20)!=1)return original_gate(page,extension,event);
    if(last_page!=page) {last_page=page;selected_icon=0xffffffffu;}
    u32 source=W(event,8);
    if(source) {
        for(u32 i=0;i<12;i++) {
            if(source!=W(page,0x244+4*i))continue;
            selected_icon=i;
            if(ready(i)) {booster_allowed++;return 1;}
            return original_gate(page,extension,event);
        }
        for(u32 i=0;i<4;i++) {
            if(source==W(page,0x274+4*i) && ready(selected_icon)) {
                booster_allowed++;return 1;
            }
        }
    }
    return original_gate(page,extension,event);
}
