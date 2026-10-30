#include <assert.h>
#include <string.h>
#include "../tools/native/bolt_assets.c"
static const char *observed;
void original_bolt0(u32 a,u32 b,const struct BoltString *p){(void)a;(void)b;observed=p?p->text:0;}
void original_bolt1(u32 a,u32 b,const struct BoltString *p){original_bolt0(a,b,p);}
void original_bolt2(u32 a,u32 b,const struct BoltString *p){original_bolt0(a,b,p);}
static void path(const char *s){struct BoltString p={s,0};bolt_format0(0,0,&p);}
int main(void) {
    path("course/Gu_Bolt00/course_model.szs");
    path("mapobj/VRWaterPark/VRWaterPark.bfres");
    assert(!strcmp(observed,"custom/bolt_assets/mapobj/VRWaterPark/VRWaterPark.bfres"));
    path("mapobj/Dossun/Dossun.bfres");assert(!strcmp(observed,"mapobj/Dossun/Dossun.bfres"));
    path("course/Gu_BcpParis/course_model.szs");
    path("mapobj/VRWaterPark/VRWaterPark.bfres");assert(!strcmp(observed,"mapobj/VRWaterPark/VRWaterPark.bfres"));
    path("/course/Gu_Bolt47/course_muunt.byaml");
    path("/mapobj/CarA/CarA.bfres");assert(!strcmp(observed,"custom/bolt_assets/mapobj/CarA/CarA.bfres"));
    path("course/Gu_Bolt48/course_model.szs");
    path("mapobj/CarA/CarA.bfres");assert(!strcmp(observed,"mapobj/CarA/CarA.bfres"));
    path("course/Gu_Menu/course_model.szs");
    path("mapobj/VRfair/VRfair.bfres");assert(!strcmp(observed,"mapobj/VRfair/VRfair.bfres"));
    bolt_format0(0,0,0);assert(!observed);
    return 0;
}
