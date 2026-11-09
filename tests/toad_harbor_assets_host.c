#define BCP_HOST
#define BCP_STRING_VTABLE 123
#include "../tools/native/toad_harbor_assets.c"
#include <assert.h>
#include <string.h>
int main(void){
 struct BcpString in={"mapobj/CiJump/CiJump.bfres",0},out;char buffer[128];
 assert(route(&in,&out,buffer)==&in);
 in.text="course/Gu_City/course_muunt.byaml";route(&in,&out,buffer);
 const char *paths[]={"mapobj/CiJump","mapobj/CiJump/","mapobj/CiJump/CiJump.bfres","mapobj/CiJump/CiJump.kcl"};
 for(unsigned i=0;i<4;i++){in.text=paths[i];assert(route(&in,&out,buffer)==&out);assert(!strncmp(out.text,"custom/vanilla/",15));assert(out.vtable==123);}
 in.text="mapobj/CiJumpOther";assert(route(&in,&out,buffer)==&in);
 const char *courses[]={"course/Gu_Bcp11/course_model.szs","course/Gu_BowserCastle/course.kcl","course/Gu_CityOther/course.kcl"};
 for(unsigned i=0;i<3;i++){in.text=courses[i];route(&in,&out,buffer);in.text=paths[2];assert(route(&in,&out,buffer)==&in);}
 return 0;
}
