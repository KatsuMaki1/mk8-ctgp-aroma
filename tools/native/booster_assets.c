/* Keep the replacement archive's shared assets local to its new Booster slots. */
typedef unsigned int u32;
struct BcpString {const char *text;u32 vtable;};
#ifndef BCP_STRING_VTABLE
#define BCP_STRING_VTABLE 0x100ffbccu
#endif
const char bcp_assets_marker[]="MK8_BOOSTER_ASSET_SCOPE_V1";
static u32 active;
volatile u32 bcp_redirects;
#include "booster_asset_list.h"
static u32 starts(const char *s,const char *p){while(*p)if(*s++!=*p++)return 0;return 1;}
static u32 equal(const char *a,const char *b){while(*a && *a==*b){a++;b++;}return !*a && !*b;}
static u32 course(const char *p){
    if(!starts(p,"Gu_Bcp"))return 0;
    if(p[6]<'0'||p[6]>'4'||p[7]<'0'||p[7]>'9'||p[8]!='/')return 0;
    u32 n=(p[6]-'0')*10+p[7]-'0';return n>=5 && n<=48;
}
static const struct BcpString *route(const struct BcpString *in,struct BcpString *out,char *buffer){
    if(!in||!in->text)return in;
    const char *p=in->text;if(*p=='/')p++;
    if(starts(p,"course/"))active=course(p+7);
    if(!active||!starts(p,"mapobj/"))return in;
    u32 h=2166136261u;for(const char *s=p;*s;s++)h=(h^(unsigned char)*s)*16777619u;
    for(u32 i=0;i<sizeof(bcp_assets)/sizeof(bcp_assets[0]);i++){
        if(h!=bcp_assets[i].hash||!equal(p,bcp_assets[i].path))continue;
        const char *prefix="custom/bcp/";u32 n=0;
        while(*prefix)buffer[n++]=*prefix++;
        while(*p && n<127)buffer[n++]=*p++;
        if(*p)return in;
        /* The caller can supply BufferedSafeString (12 bytes). Its virtual
         * ensureTerminated reads capacity at +8. This replacement is a plain
         * 8-byte SafeString; copying the buffered vtable corrupts memory. */
        buffer[n]=0;out->text=buffer;out->vtable=BCP_STRING_VTABLE;bcp_redirects++;return out;
    }
    return in;
}
#ifndef BCP_HOST
typedef void (*Format)(u32,u32,const struct BcpString*);
void bcp_format0(u32 d,u32 o,const struct BcpString *p){struct BcpString s;char b[128];((Format)BCP_ORIGINAL0)(d,o,route(p,&s,b));}
void bcp_format1(u32 d,u32 o,const struct BcpString *p){struct BcpString s;char b[128];((Format)BCP_ORIGINAL1)(d,o,route(p,&s,b));}
void bcp_format2(u32 d,u32 o,const struct BcpString *p){struct BcpString s;char b[128];((Format)BCP_ORIGINAL2)(d,o,route(p,&s,b));}
#endif
