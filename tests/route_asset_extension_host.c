#include <assert.h>
#include <string.h>
#define ROUTE_ASSET_HOST
#include "../tools/native/route_asset_extension.c"
int main(void){
 char path[256]="/vol/aoc0005000c1010ed00/0013/mapobj/DrawBridge/DrawBridge.bfres";
 char untouched[256];strcpy(untouched,path);rewrite(path);assert(!strcmp(path,untouched));
 char course[256]="/vol/content/course/Gu_Bcp17/course_muunt_200.byaml";rewrite(course);assert(london);
 rewrite(path);assert(!strcmp(path,"/vol/content/custom/bcp/mapobj/DrawBridge/DrawBridge.bfres"));
 char other[256]="/vol/content/course/Gu_City/course_model.szs";rewrite(other);strcpy(path,untouched);rewrite(path);assert(!strcmp(path,untouched));
 char us[256]="/vol/aoc0005000c1010ec00/0013/course/Gu_Bcp17/course_model.szs";rewrite(us);assert(london);
 char usfile[256]="/vol/aoc0005000c1010ec00/0013/mapobj/DrawBridge/DrawBridge.bfres";rewrite(usfile);assert(!strcmp(usfile,"/vol/content/custom/bcp/mapobj/DrawBridge/DrawBridge.bfres"));
 rewrite(0);return 0;
}
