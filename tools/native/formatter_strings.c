/* Older chained routers copy the input vtable into an eight-byte temporary.
 * Terminate the original while its full buffer object is available, then pass
 * a plain SafeString so no inner router treats a temporary as BufferedString. */
typedef unsigned int u32;
struct SafeString {const char *text;u32 vtable;};
const char formatter_strings_marker[]="MK8_FORMATTER_PLAIN_STRINGS_V1";
static const struct SafeString *plain(const struct SafeString *in,struct SafeString *out){
    if(!in||!in->text)return in;
#ifndef FORMATTER_HOST
    ((void(*)(const struct SafeString*))*(u32*)(in->vtable+0x14))(in);
#else
    extern void host_terminate(const struct SafeString*);
    host_terminate(in);
#endif
    out->text=in->text;out->vtable=0x100ffbccu;return out;
}
#ifndef FORMATTER_HOST
#define DLC_PATHS_HOST
#include "dlc_custom_paths.c"
typedef void (*Format)(u32,u32,const struct SafeString*);
static void after(u32 o){if(o)rewrite(*(char **)(__UINTPTR_TYPE__)o);}
void bcp_format0(u32 d,u32 o,const struct SafeString *p){struct SafeString s;((Format)BCP_ORIGINAL0)(d,o,plain(p,&s));after(o);}
void bcp_format1(u32 d,u32 o,const struct SafeString *p){struct SafeString s;((Format)BCP_ORIGINAL1)(d,o,plain(p,&s));after(o);}
void bcp_format2(u32 d,u32 o,const struct SafeString *p){struct SafeString s;((Format)BCP_ORIGINAL2)(d,o,plain(p,&s));after(o);}
#endif
