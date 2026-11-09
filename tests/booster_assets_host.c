#define BCP_HOST
#define BCP_STRING_VTABLE 123
#include "../tools/native/booster_assets.c"
#include <assert.h>
#include <string.h>
int main(void){
    struct BcpString out,in={"course/Gu_Bcp05/course_model.szs",0x100ffc14u};char buffer[128];
    assert(route(&in,&out,buffer)==&in);
    in.text="mapobj/VRfair/VRfair.bfres";
    assert(route(&in,&out,buffer)==&out);
    assert(!strcmp(out.text,"custom/bcp/mapobj/VRfair/VRfair.bfres") && out.vtable==123);
    in.text="mapobj/VRfair";assert(route(&in,&out,buffer)==&out);
    assert(!strcmp(out.text,"custom/bcp/mapobj/VRfair"));
    in.text="mapobj/VRfair/";assert(route(&in,&out,buffer)==&out);
    assert(!strcmp(out.text,"custom/bcp/mapobj/VRfair/"));
    in.text="mapobj/VRfairOther";assert(route(&in,&out,buffer)==&in);
    in.text="mapobj/VRfair/VRfair.kcl";assert(route(&in,&out,buffer)==&in);
    const char *invalid[]={"Gu_Bcp04","Gu_Bcp49","Gu_Bcp005","Gu_BcpParis","Gu_Bolt05","Gu_DarkSanctuaryWiiu"};
    for(unsigned int i=0;i<sizeof(invalid)/sizeof(invalid[0]);i++){
        char path[100];strcpy(path,"course/");strcat(path,invalid[i]);strcat(path,"/course.kcl");in.text=path;route(&in,&out,buffer);
        in.text="mapobj/VRfair/VRfair.bfres";assert(route(&in,&out,buffer)==&in);
    }
    in.text="/course/Gu_Bcp48/course_muunt.byaml";route(&in,&out,buffer);
    in.text="/mapobj/VRfair/VRfair.bfres";assert(route(&in,&out,buffer)==&out);
    in.text="course/Gu_FirstCircuit/course.kcl";route(&in,&out,buffer);
    in.text="mapobj/VRfair/VRfair.bfres";assert(route(&in,&out,buffer)==&in);
    assert(route(0,&out,buffer)==0);return 0;
}
