/* EUR81 solo experiment. Keep native turbo enums at 0..2. */
typedef unsigned int u32;
#ifndef PINK_HOST
#define W(p,o) (*(u32 *)((unsigned char *)(__UINTPTR_TYPE__)(p)+(o)))
#define F(p,o) (*(float *)((unsigned char *)(__UINTPTR_TYPE__)(p)+(o)))
#define B(p,o) (*(unsigned char *)((unsigned char *)(__UINTPTR_TYPE__)(p)+(o)))
#endif
const char pink_marker[]="MK8_PINK_DRIFT_EUR81_V1";
volatile u32 pink_charges, pink_boosts, pink_tints;
struct Tint {u32 set,id;float r,g,b;};
struct Player {u32 vehicle,pending;struct Tint tint[5];};
static struct Player players[12];
extern void original_drift(u32,u32,u32);
extern int original_dash(u32,u32,u32,int);
extern void original_sparks(u32);
static int charged(u32 drift) {
    u32 state=W(drift,8);
    return state>=4 && state<=7 && W(drift,0x6c)==2 && F(drift,0x68)>=900.f;
}
static struct Player *player(u32 vehicle) {
    u32 id=W(vehicle,0x50);
    if(id>=12 || !B(vehicle,0x64) || B(vehicle,0x66))return 0;
    struct Player *p=&players[id];
    if(p->vehicle!=vehicle) {
        p->vehicle=vehicle;p->pending=0;
        for(u32 i=0;i<5;i++)p->tint[i].set=0;
    }
    return p;
}
void pink_drift(u32 drift,u32 output,u32 input) {
    struct Player *p=player(W(drift,4));
    int before=p?charged(drift):0;
    original_drift(drift,output,input);
    if(p) {
        p->pending=before && W(output,0x20)==2;
        if(!before && charged(drift))pink_charges++;
    }
}
int pink_dash(u32 dash,u32 kind,u32 sound,int duration) {
    struct Player *p=player(W(dash,4));
    if(p && kind==8 && p->pending) {
        u32 base=W(dash,0x74);
        if(duration>=0)base=(u32)duration;
        if(base>0 && base<=600) {duration=(int)(base+base/2);pink_boosts++;}
        p->pending=0;
    }
    return original_dash(dash,kind,sound,duration);
}
static void tint(struct Tint *saved,u32 handle,int active) {
    if(!handle)return;
    u32 effect=W(handle,0);
    if(!effect || W(effect,0x1c)!=W(handle,4))return;
    u32 set=W(effect,0x20),id=W(effect,0x24);
    if(!set || id!=W(set,0x1d0) || !W(set,0x1dc) || W(set,0x1e0)>16)return;
    if(active) {
        if(saved->set!=set || saved->id!=id) {
            saved->set=set;saved->id=id;
            saved->r=F(set,0x278);saved->g=F(set,0x27c);saved->b=F(set,0x280);
        }
        /* Per-set tint, never edit shared PTCL resources. Visual needs a race test. */
        F(set,0x278)=saved->r;F(set,0x27c)=saved->g*.08f;F(set,0x280)=saved->b*6.f;
        pink_tints++;
    } else if(saved->set==set && saved->id==id) {
        F(set,0x278)=saved->r;F(set,0x27c)=saved->g;F(set,0x280)=saved->b;
        saved->set=0;
    }
}
void pink_sparks(u32 effects) {
    original_sparks(effects);
    u32 vehicle=W(effects,0x40),move=vehicle?W(vehicle,0x14):0;
    struct Player *p=vehicle?player(vehicle):0;
    if(!p || !move)return;
    u32 drift=W(move,0xec);
    if(!drift)return;
    int active=charged(drift);
    static const u32 offsets[5]={0x74,0x80,0x88,0x90,0x98};
    for(u32 i=0;i<5;i++)tint(&p->tint[i],W(effects,offsets[i]),active);
}
