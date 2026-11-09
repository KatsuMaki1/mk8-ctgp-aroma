#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "../tools/native/tt_category.h"
int main(void){
 const struct CtgpTTTrack tracks[]={
  {"Gu_FirstCustom","ct.first","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
  {"Gu_SecondCustom","ct.second","bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}
 };
 struct CtgpTTCategory selected;char first150[256],first200[256],second[256],pink[256],tiny[4];
 assert(ctgp_tt_select(&selected,tracks,2,"Gu_FirstCustom",2,0));assert(ctgp_tt_path(&selected,first150,sizeof(first150)));assert(!strcmp(first150,"custom/tt/v1/ct.first/aaaaaaaa/150/n1/"));assert(strlen(first150)<60); /* Windows 260-char limit with a ~118-char native filename */
 assert(ctgp_tt_select(&selected,tracks,2,"Gu_FirstCustom",3,0));assert(ctgp_tt_path(&selected,first200,sizeof(first200)));assert(strcmp(first150,first200));
 assert(ctgp_tt_select(&selected,tracks,2,"Gu_SecondCustom",2,0));assert(ctgp_tt_path(&selected,second,sizeof(second)));assert(strcmp(first150,second));
 assert(ctgp_tt_select(&selected,tracks,2,"Gu_FirstCustom",2,1));assert(ctgp_tt_path(&selected,pink,sizeof(pink)));assert(strcmp(first150,pink));
 assert(!ctgp_tt_path(&selected,tiny,sizeof(tiny))&&!tiny[0]);
 assert(!ctgp_tt_select(&selected,tracks,2,"UnknownCustom",2,0));assert(!selected.track&&!ctgp_tt_path(&selected,tiny,sizeof(tiny)));
 assert(!ctgp_tt_select(&selected,tracks,2,"Gu_FirstCustom",4,0));
 puts("TT identities isolate custom tracks, 150/200, physics, and reject unknown donors");
}
