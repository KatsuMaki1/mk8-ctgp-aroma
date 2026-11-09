/* Match complete formatted paths AFTER the existing formatter chain. */
typedef unsigned int u32;
const char route_asset_extension_marker[]="CTGP_LONDON_BRIDGE_RESOURCE_V2";
static u32 london;
volatile u32 route_asset_course_matches,route_asset_file_redirects;
static u32 starts(const char *s,const char *p){while(*p)if(*s++!=*p++)return 0;return 1;}
static u32 equal(const char *a,const char *b){while(*a&&*a==*b){a++;b++;}return !*a&&!*b;}
static const char *relative(const char *p){
 for(u32 i=0;i<4;i++)if(!p[i]||!((p[i]>='0'&&p[i]<='9')||(p[i]>='a'&&p[i]<='f')||(p[i]>='A'&&p[i]<='F')))return p;
 return p[4]=='/'?p+5:p;
}
static void rewrite(char *path){
 if(!path)return;
 u32 aoc=starts(path,"/vol/aoc0005000c1010ed00/")||starts(path,"/vol/aoc0005000c1010ec00/")||starts(path,"/vol/aoc0005000c1010eb00/");
 const char *p=0;
 if(aoc)p=relative(path+25);
 else if(starts(path,"/vol/content/"))p=path+13;
 else return;
 if(starts(p,"course/")){london=starts(p,"course/Gu_Bcp17/");if(london)route_asset_course_matches++;}
 if(!aoc||!london||!equal(p,"mapobj/DrawBridge/DrawBridge.bfres"))return;
 const char *target="/vol/content/custom/bcp/mapobj/DrawBridge/DrawBridge.bfres";
 u32 old_length=0,new_length=0;while(path[old_length])old_length++;while(target[new_length])new_length++;
 if(new_length>old_length)return; /* No dependency on the caller's capacity. */
 for(u32 i=0;i<=new_length;i++)path[i]=target[i];
 route_asset_file_redirects++;
}
#ifndef ROUTE_ASSET_HOST
typedef void(*Format)(u32,u32,u32);
static void after(u32 output){if(output)rewrite(*(char**)(__UINTPTR_TYPE__)output);}
void route_asset_format0(u32 d,u32 o,u32 p){((Format)ROUTE_ORIGINAL0)(d,o,p);after(o);}
void route_asset_format1(u32 d,u32 o,u32 p){((Format)ROUTE_ORIGINAL1)(d,o,p);after(o);}
void route_asset_format2(u32 d,u32 o,u32 p){((Format)ROUTE_ORIGINAL2)(d,o,p);after(o);}
#endif
