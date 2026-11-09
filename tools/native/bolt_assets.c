/* Keep supplied global object overrides local to Boltthunder4's courses. */
typedef unsigned int u32;
struct BoltString {const char *text;u32 vtable;};
extern void original_bolt0(u32,u32,const struct BoltString*);
extern void original_bolt1(u32,u32,const struct BoltString*);
extern void original_bolt2(u32,u32,const struct BoltString*);
const char bolt_assets_marker[]="MK8_BOLT_ASSET_SCOPE_V1";
static u32 bolt_active;
volatile u32 bolt_asset_redirects;
static const char *assets[]={
 "mapobj/CarA/CarA.bfres","mapobj/N64RStar/N64RStar.bfres",
 "mapobj/N64RStart/N64RStart.bfres","mapobj/TreeSnow/TreeSnow.bfres",
 "mapobj/VR64Peach/VR64Peach.bfres","mapobj/VRfair/VRfair.bfres",
 "mapobj/VROcean/VROcean.bfres","mapobj/VRWaterPark/VRWaterPark.bfres",
 "mapobj/DL_Rupee/DL_Rupee.bfres","mapobj/DL_Rupee/SNDG_KTOBJ_DL_Rupee.bars",
 "mapobj/DL_Bell/DL_Bell.bfres","mapobj/DL_Bell/SNDG_KTOBJ_DL_Bell.bars"};
static const char *private_assets[]={
 "custom/bolt_assets/mapobj/CarA/CarA.bfres","custom/bolt_assets/mapobj/N64RStar/N64RStar.bfres",
 "custom/bolt_assets/mapobj/N64RStart/N64RStart.bfres","custom/bolt_assets/mapobj/TreeSnow/TreeSnow.bfres",
 "custom/bolt_assets/mapobj/VR64Peach/VR64Peach.bfres","custom/bolt_assets/mapobj/VRfair/VRfair.bfres",
 "custom/bolt_assets/mapobj/VROcean/VROcean.bfres","custom/bolt_assets/mapobj/VRWaterPark/VRWaterPark.bfres",
 "custom/bolt_assets/mapobj/DL_Rupee/DL_Rupee.bfres","custom/bolt_assets/mapobj/DL_Rupee/SNDG_KTOBJ_DL_Rupee.bars",
 "custom/bolt_assets/mapobj/DL_Bell/DL_Bell.bfres","custom/bolt_assets/mapobj/DL_Bell/SNDG_KTOBJ_DL_Bell.bars"};
static u32 starts(const char *s,const char *prefix) {
    while(*prefix)if(*s++!=*prefix++)return 0;
    return 1;
}
static u32 equal(const char *a,const char *b) {
    while(*a && *a==*b){a++;b++;}
    return !*a && !*b;
}
static u32 is_bolt_course(const char *p) {
    if(!starts(p,"Gu_Bolt"))return 0;
    return p[7]>='0' && p[7]<='4' && p[8]>='0' && p[8]<='9'
        && (p[7]!='4' || p[8]<='7') && p[9]=='/';
}
static const struct BoltString *bolt_route(const struct BoltString *path,struct BoltString *out) {
    if(!path || !path->text)return path;
    const char *p=path->text;if(*p=='/')p++;
    if(starts(p,"course/"))bolt_active=is_bolt_course(p+7);
    if(bolt_active)for(u32 i=0;i<sizeof(assets)/sizeof(assets[0]);i++) {
        if(equal(p,assets[i])) {
            out->text=private_assets[i];out->vtable=0x100ffbccu;bolt_asset_redirects++;
            return out;
        }
    }
    return path;
}
void bolt_format0(u32 device,u32 out,const struct BoltString *path) {
    struct BoltString redirected;original_bolt0(device,out,bolt_route(path,&redirected));
}
void bolt_format1(u32 device,u32 out,const struct BoltString *path) {
    struct BoltString redirected;original_bolt1(device,out,bolt_route(path,&redirected));
}
void bolt_format2(u32 device,u32 out,const struct BoltString *path) {
    struct BoltString redirected;original_bolt2(device,out,bolt_route(path,&redirected));
}
