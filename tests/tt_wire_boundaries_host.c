#include <assert.h>
#include "tt_category.h"
typedef unsigned int u32;
static u32 active=1,tt_selected_valid=1,tt_selected_native_course=29;
static struct CtgpTTCategory tt_selected_category;
#define W(p,o) (active)
static unsigned host_system(void){return 1;}
#define FN(a,t) ((t)host_system)
#define TT_WIRE_HOST
#include "tt_wire_module.c"
static u32 seen,calls,selected_country,last_row_country,last_row_wheel;
u32 tt_options_country(void){return selected_country;}
void original_tt_country_profile(u32 source,u32 output,u32 own){(void)source;(void)output;(void)own;}
void original_tt_country_row(u32 row,u32 time,u32 pid,u32 country,u32 wheel){(void)row;(void)time;(void)pid;last_row_country=country;last_row_wheel=wheel;}
void original_tt_wire_upload(u32 manager,u32 owner,const u32 *course,u32 name,u32 time,u32 flag){
 assert(manager==1&&owner==2&&name==3&&time==4&&flag==5);seen=*course;calls++;
}
void original_tt_wire_query(u32 manager,const u32 *course,u32 scope){assert(manager==1&&scope==2);seen=*course;calls++;}
void original_tt_wire_score(u32 manager,const u32 *course,u32 time,u32 unused,u32 high,u32 low,u32 flag){
 assert(manager==1&&time==3&&unused==4&&high==5&&low==6&&flag==7);seen=*course;calls++;
}
u32 original_tt_wire_target(const u32 *course){seen=*course;calls++;return (*course-16)&0xffff;}
int main(void){
 const struct CtgpTTWireTrack *row=&ctgp_tt_wire_tracks[0];
 struct CtgpTTTrack track={"unused",row->id,row->revision};
 tt_selected_category=(struct CtgpTTCategory){&track,200,1};
 u32 course=29,expected=row->base+3+16;
 tt_wire_upload(1,2,&course,3,4,5);assert(seen==expected&&course==29);
 tt_wire_query(1,&course,2);assert(seen==expected&&course==29);
 tt_wire_score(1,&course,3,4,5,6,7);assert(seen==expected&&course==29&&tt_wire_scores==1);
 assert(tt_wire_target(&course)==expected-16&&course==29);
 /* Already-remapped targets must not be mapped a second time. */
 assert(tt_wire_target(&expected)==expected-16);
 active=0;tt_wire_query(1,&course,2);assert(seen==29);active=1;
 tt_selected_valid=0;tt_wire_query(1,&course,2);assert(seen==29);tt_selected_valid=1;
 struct CtgpTTTrack unknown={"unused","ct.unknown",row->revision};
 tt_selected_category.track=&unknown;
 u32 before=calls;tt_wire_upload(1,2,&course,3,4,5);assert(calls==before);
 assert(tt_wire_target(&course)==0xffff&&calls==before);
 selected_country=219;tt_country_row(11,123,1,0,7);assert(last_row_country==219&&last_row_wheel==7);
 tt_country_row(11,123,2,77,0);assert(last_row_country==77&&last_row_wheel==0);
 active=0;tt_country_row(11,123,1,77,7);assert(last_row_country==77&&last_row_wheel==7);
 return 0;
}
