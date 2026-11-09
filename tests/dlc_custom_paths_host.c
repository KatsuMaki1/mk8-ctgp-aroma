#define DLC_PATHS_HOST
#include "../tools/native/dlc_custom_paths.c"
#include <assert.h>
#include <string.h>
#include <stdio.h>
int main(void){
 char b[512];const char *regions[]={"ed","ec","eb"};
 strcpy(b,"/vol/aoc0005000c1010ed00/0019/course/Gu_Bcp48/course.bglpbd");rewrite(b);assert(!strcmp(b,"/vol/content/course/Gu_Bcp48/course.bglpbd"));
 active_custom_course=0;rewrite(0);strcpy(b,"/vol/aoc0005000c1010ed00/mapobj/CiJump/CiJump.bfres");rewrite(b);assert(strstr(b,"/vol/aoc")==b);
 for(unsigned i=0;i<3;i++){
  snprintf(b,sizeof b,"/vol/aoc0005000c1010%s00/course/Gu_Bcp48/course_muunt_200.byaml",regions[i]);rewrite(b);assert(!strcmp(b,"/vol/content/course/Gu_Bcp48/course_muunt_200.byaml"));
 }
 strcpy(b,"/vol/aoc0005000c1010ed00/custom/bcp/mapobj/VRCnsw68/VRCnsw68.bfres");rewrite(b);assert(strstr(b,"/vol/content/")==b);
 strcpy(b,"/vol/aoc0005000c1010ed00/course/Du_BigBlue/course_model.szs");rewrite(b);assert(strstr(b,"/vol/aoc")==b);
 strcpy(b,"/vol/aoc0005000c1010ed00/mapobj/CiJump/CiJump.bfres");rewrite(b);assert(strstr(b,"/vol/aoc")==b);
 const char *unchanged[]={"/vol/aoc0005000c1010ed00/data","/vol/aoc0005000c1010ed00/ui/cmn/menu.szs","/vol/aoc0005000c1010ed00","/vol/aoc0005000c1010ed00/course/Gu_Bcp48/../Du_BigBlue/course.kcl","/vol/content/course/Gu_City/course.kcl"};
 for(unsigned i=0;i<5;i++){strcpy(b,unchanged[i]);rewrite(b);assert(!strcmp(b,unchanged[i]));}
 strcpy(b,"/vol/content/course/Gu_Bcp48/course.kcl");rewrite(b);assert(active_custom_course);
 strcpy(b,"/vol/aoc0005000c1010ed00/audio/turbo_sound.bfsar");rewrite(b);assert(!strcmp(b,"/vol/content/audio/turbo_sound.bfsar"));
 strcpy(b,"/vol/aoc0005000c1010ed00/mapobj/CmnPatapata/CmnPatapata.bfres");rewrite(b);assert(!strcmp(b,"/vol/content/mapobj/CmnPatapata/CmnPatapata.bfres"));
 strcpy(b,"/vol/aoc0005000c1010ed00/0019/mapobj/DL_TicketGate/DL_TicketGate.bfres");rewrite(b);assert(!strcmp(b,"/vol/content/custom/bcp/mapobj/DL_TicketGate/DL_TicketGate.bfres"));
 strcpy(b,"/vol/aoc0005000c1010ed00/0019/course/Du_Metro/course.kcl");rewrite(b);assert(!active_booster_course);
 strcpy(b,"/vol/aoc0005000c1010ed00/0019/mapobj/DL_TicketGate/DL_TicketGate.bfres");rewrite(b);assert(strstr(b,"/vol/aoc")==b);
 return 0;
}
