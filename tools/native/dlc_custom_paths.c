/* Rewrite only already-formatted custom file paths, never the AOC mount. */
typedef unsigned int u32;
const char dlc_paths_marker[]="MK8_CUSTOM_AOC_PATHS_V1";
volatile u32 dlc_path_redirects;
char dlc_current_course[64];
static u32 active_custom_course;
static u32 active_booster_course;
#include "booster_asset_list.h"
static u32 starts(const char *s,const char *p){while(*p)if(*s++!=*p++)return 0;return 1;}
static u32 equal(const char *a,const char *b){while(*a && *a==*b){a++;b++;}return !*a && !*b;}
static const char *content_relative(const char *p){
    for(u32 i=0;i<4;i++)if(!p[i] || !((p[i]>='0' && p[i]<='9') || (p[i]>='a' && p[i]<='f') || (p[i]>='A' && p[i]<='F')))return p;
    return p[4]=='/'?p+5:p;
}
static u32 listed(const char *p){
    u32 h=2166136261u;for(const char *s=p;*s;s++)h=(h^(unsigned char)*s)*16777619u;
    for(u32 i=0;i<sizeof(bcp_assets)/sizeof(bcp_assets[0]);i++)
        if(h==bcp_assets[i].hash && equal(p,bcp_assets[i].path))return 1;
    return 0;
}
static void rewrite(char *path){
    if(!path)return;
    const char *relative=0;
    u32 aoc=starts(path,"/vol/aoc0005000c1010ed00/") || starts(path,"/vol/aoc0005000c1010ec00/") || starts(path,"/vol/aoc0005000c1010eb00/");
    if(aoc)relative=content_relative(path+25);
    else if(starts(path,"/vol/content/"))relative=path+13;
    else return;
    if(starts(relative,"course/")) {
        const char *name=relative+7;u32 n=0;
        while(name[n] && name[n]!='/' && n<sizeof dlc_current_course-1){dlc_current_course[n]=name[n];n++;}
        dlc_current_course[n]=0;
        active_custom_course=listed(relative);
        const char *c=relative+7;
        active_booster_course=active_custom_course && starts(c,"Gu_Bcp")
            && c[6]>='0' && c[6]<='4' && c[7]>='0' && c[7]<='9' && c[8]=='/'
            && ((c[6]-'0')*10+c[7]-'0')>=5;
    }
    if(!aoc)return;
    char overlay[512];u32 private_overlay=0;
    if(active_booster_course && starts(relative,"mapobj/")) {
        u32 n=0;while(relative[n] && n<sizeof overlay-12)n++;
        if(!relative[n]) {
            const char *prefix="custom/bcp/";u32 j=0;
            while(*prefix)overlay[j++]=*prefix++;
            for(u32 i=0;i<=n;i++)overlay[j+i]=relative[i];
            if(listed(overlay))private_overlay=1;
        }
    }
    if(!private_overlay && !listed(relative))return;
    /* Shared objects/music are eligible only while loading a custom course.
     * Private custom/ paths and listed course paths are intrinsically scoped. */
    if(!starts(relative,"course/") && !starts(relative,"custom/") && !active_custom_course)return;
    /* AOC's 25-byte prefix is at least 12 bytes longer than /vol/content/;
     * adding custom/bcp/ (11 bytes) still fits the original pathname buffer. */
    char *out=path+13;const char *in=private_overlay?overlay:relative;
    do{*out++=*in;}while(*in++);
    const char *prefix="/vol/content/";for(u32 i=0;i<13;i++)path[i]=prefix[i];
    dlc_path_redirects++;
}
#ifndef DLC_PATHS_HOST
typedef void (*Format)(u32,u32,u32);
static void after(u32 o){if(o)rewrite(*(char **)(__UINTPTR_TYPE__)o);}
void bcp_format0(u32 d,u32 o,u32 p){((Format)BCP_ORIGINAL0)(d,o,p);after(o);}
void bcp_format1(u32 d,u32 o,u32 p){((Format)BCP_ORIGINAL1)(d,o,p);after(o);}
void bcp_format2(u32 d,u32 o,u32 p){((Format)BCP_ORIGINAL2)(d,o,p);after(o);}
#endif
