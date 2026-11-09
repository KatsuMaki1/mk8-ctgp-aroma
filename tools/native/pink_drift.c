/* EUR81 opt-in experiment: native turbo enums remain 0..2. */
typedef unsigned int u32;
#ifndef W
#define W(p,o) (*(u32 *)((unsigned char *)(__UINTPTR_TYPE__)(p)+(o)))
#endif
#ifndef F
#define F(p,o) (*(float *)((unsigned char *)(__UINTPTR_TYPE__)(p)+(o)))
#endif
#ifndef B
#define B(p,o) (*(unsigned char *)((unsigned char *)(__UINTPTR_TYPE__)(p)+(o)))
#endif
extern volatile u32 pink_enabled;
const char pink_marker[]="MK8_PINK_DRIFT_EUR81_V1";
volatile u32 pink_charges, pink_boosts, pink_tints;
struct Player {u32 vehicle,pending;};
static struct Player players[12];
extern void original_drift(u32,u32,u32);
extern int original_dash(u32,u32,u32,int);
static int charged(u32 drift) {
    u32 state=W(drift,8);
    return state>=4 && state<=7 && W(drift,0x6c)==2 && F(drift,0x68)>=900.f;
}
static struct Player *player(u32 vehicle) {
    if(!vehicle)return 0;
    u32 id=W(vehicle,0x50);
    if(id>=12 || !B(vehicle,0x64) || B(vehicle,0x66))return 0;
    struct Player *p=&players[id];
    if(p->vehicle!=vehicle) {
        p->vehicle=vehicle;p->pending=0;
    }
    return p;
}
void pink_drift(u32 drift,u32 output,u32 input) {
    struct Player *p=player(W(drift,4));
    int before=p && pink_enabled?charged(drift):0;
    float old_charge=F(drift,0x68);
    original_drift(drift,output,input);
    if(p) {
        u32 state=W(drift,8);float gain=F(drift,0x68)-old_charge;
        if(pink_enabled&&state>=4&&state<=7&&gain>0.f&&gain<100.f)
            F(drift,0x68)+=gain*.5f;
        p->pending=before && W(output,0x20)==2;
        if(pink_enabled && !before && charged(drift))pink_charges++;
    }
}
int pink_dash(u32 dash,u32 kind,u32 sound,int duration) {
    struct Player *p=player(W(dash,4));
    if(p && pink_enabled && kind==8 && p->pending) {
        u32 base=W(dash,0x74);
        if(duration>=0)base=(u32)duration;
        if(base>0 && base<=600) {duration=(int)(base+base/2);pink_boosts++;}
        p->pending=0;
    }
    if(p && kind==8)p->pending=0;
    return original_dash(dash,kind,sound,duration);
}
