/* Cemu EUR v81 prototype. UI state only; original gameplay is untouched. */
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
#define W(p,o) (*(volatile u32 *)((u32)(p)+(o)))
#define B(p,o) (*(volatile u8 *)((u32)(p)+(o)))
#define FN(a,t) ((t)(a))
struct String { const char *text; u32 vtable; };
extern void original_format0(u32,u32,const struct String*);
extern void original_format1(u32,u32,const struct String*);
extern void original_format2(u32,u32,const struct String*);
extern void original_create(u32);
extern void original_event(u32,u32);
extern void original_hud(u32);
const char options_marker[]="MK8_GAME_OPTIONS_EUR81_V1";
static u32 enabled=1;
static u32 button;
static u32 dark_course;
volatile u32 sky_redirects;
volatile u32 course_observations;
static const char dark[]="Gu_DarkSanctuaryWiiu/";
struct AssetRoute {const char *from;const char *to;};
#define ASSET(p) {"mapobj/" p,"custom/course_assets/Gu_DarkSanctuaryWiiu/mapobj/" p}
static const struct AssetRoute assets[]={
    ASSET("VRfair/VRfair.bfres"),ASSET("DKBanana/DKBanana.bfres"),
    ASSET("Dossun/Dossun.bfres"),ASSET("Dossun/SNDG_Dossun.bars"),
    ASSET("JungleBird/JungleBird.bfres"),ASSET("Sanbo/Sanbo.bfres"),
    ASSET("Sanbo/SNDG_Sanbo.bars"),ASSET("TikiTak/TikiTak.bfres"),
    ASSET("TikiTak/SNDG_TikiTak.bars")
};
static u32 starts(const char *s,const char *prefix) {
    while(*prefix)if(*s++!=*prefix++)return 0;
    return 1;
}
static const struct String *route(const struct String *path,struct String *out) {
    if(!path || !path->text)return path;
    const char *p=path->text;
    if(*p=='/')p++;
    /* Device-relative paths are used here, before the /vol prefix is formed. */
    if(starts(p,"course/")) {
        dark_course=starts(p+7,dark);
        course_observations++;
    }
    if(dark_course) {
        for(u32 i=0;i<sizeof(assets)/sizeof(assets[0]);i++) {
            const char *a=p,*b=assets[i].from;
            while(*a && *a==*b) {a++;b++;}
            if(!*a && !*b) {
                out->text=assets[i].to;out->vtable=0x100ffbccu;sky_redirects++;
                return out;
            }
        }
    }
    return path;
}
void options_format0(u32 device,u32 out,const struct String *path) {
    struct String redirected;original_format0(device,out,route(path,&redirected));
}
void options_format1(u32 device,u32 out,const struct String *path) {
    struct String redirected;original_format1(device,out,route(path,&redirected));
}
void options_format2(u32 device,u32 out,const struct String *path) {
    struct String redirected;original_format2(device,out,route(path,&redirected));
}
static void label(void) {
    static const u16 on[]={'S','p','e','e','d','o','m','e','t','e','r',' ',':',' ','O','N',0};
    static const u16 off[]={'S','p','e','e','d','o','m','e','t','e','r',' ',':',' ','O','F','F',0};
    struct String name={"T_BtnText_00",0x100e10f8};
    if(button)FN(0x02536888,void(*)(u32,const struct String*,const u16*))(button,&name,enabled?on:off);
}
static u32 reserve_control(u32 page) {
    if(W(page,0x20)<W(page,0x24))return 1;
    u32 count=W(page,0x20),old=W(page,0x28);
    if(count>128)return 0;
    u32 array=FN(0x02721868,u32(*)(u32))((count+4)*4);
    if(!array)return 0;
    for(u32 i=0;i<count;i++)W(array,i*4)=W(old,i*4);
    W(page,0x28)=array;W(page,0x24)=count+4;
    return 1;
}
void options_create(u32 page) {
    original_create(page);
    if(W(page,4)!=25 || !reserve_control(page))return;
    u32 control=FN(0x02721868,u32(*)(u32))(0x114);
    if(!control)return;
    for(u32 i=0;i<0x114;i++)B(control,i)=0;
    FN(0x025789b4,u32(*)(u32))(control);
    W(control,0x54)=0x100d5a2c;W(control,0x64)=0x100d5b34;
    FN(0x02534530,u32(*)(u32))(control+0xf4);
    W(control,0x24)=3;
    struct String name={"P_Speedometer_00",0x100e10f8};
    FN(0x0253ecf4,void(*)(u32,u32,u32,const struct String*))(page,control,W(page,0x260),&name);
    /* A settings toggle has no destination page. Native decide checks this
     * pointer after emitting our event; leaving it set launches a stale flow. */
    W(control,0)=13;W(control,0xd8)=0;
    button=control;
    W(page,0x244)|=8;
    label();
}
void options_event(u32 page,u32 event) {
    if(W(page,4)==25) {
        if(W(event,8) && W(event,0x0c)==13) {
            if(W(event,0x14)==2) {enabled^=1;label();}
            return;
        }
        if(!W(event,8) && W(event,0)==page+0x230 && (W(event,0x1c)&8)) {
            enabled^=1;label();return;
        }
    }
    original_event(page,event);
}
void options_hud(u32 arg) {
    original_hud(arg);
    u32 control=W(0x10302588,0);
    if(!control)return;
    const char *names[]={"L_Speedometer_00","W_Speedo_00","W_Speedo_01","P_Speedo_00"};
    for(u32 i=0;i<4;i++) {
        struct String name={names[i],0x100e10f8};
        u32 pane=FN(0x02531718,u32(*)(u32,const struct String*))(control,&name);
        if(pane)B(pane,0x44)=(B(pane,0x44)&~1u)|(enabled?1:0);
    }
}
