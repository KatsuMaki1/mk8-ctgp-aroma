/* Capture a TT category on the accepted CourseVS DECIDE event, before native
 * transition to Ghost. Never consult the last loaded resource pathname. */
#include "tt_category.h"
#include "catalog_next.h"
#ifndef TT_CAPTURE_STRING
#define TT_CAPTURE_STRING(address) ((const char *)(__UINTPTR_TYPE__)(address))
#endif
extern void original_tt_course_event(u32,u32);
volatile u32 tt_selected_valid,tt_selected_status,tt_selected_count;
volatile u32 tt_selected_native_course,tt_selected_page,tt_selected_slot;
struct CtgpTTCategory tt_selected_category;
volatile u32 tt_selected_name_message,tt_selected_prefix_message;
#ifdef ENABLE_TT_GHOST_SCOPE
static u8 tt_selected_preview_map[28];static u32 tt_selected_preview_ready;
static void tt_capture_preview(u32 source){
 tt_selected_preview_ready=0;u32 picture=W(source,0x104);
 if(!picture||!W(picture,8))return;
 u32 method=W(W(picture,8),0x4c);if(!method)return;
 u32 material=FN(method,u32(*)(u32,u32))(picture,0),maps=material?W(material,0x10):0;
 if(!maps||!W(maps,0x1c))return;
 for(u32 i=0;i<28;i++)tt_selected_preview_map[i]=B(maps,0x1c+i);
 tt_selected_preview_ready=1;
}
#endif
char tt_selected_directory[64],tt_selected_identity[96],tt_selected_revision[65],tt_selected_path[256];
static void tt_selected_clear(void){
 tt_selected_name_message=tt_selected_prefix_message=0;tt_selected_valid=0;tt_selected_category.track=0;tt_selected_category.cc=0;tt_selected_category.pink=0;
 tt_selected_directory[0]=tt_selected_identity[0]=tt_selected_revision[0]=tt_selected_path[0]=0;
}
static int tt_selected_copy(char *out,u32 size,const char *in){
 u32 i=0;if(!in||!size)return 0;
 while(in[i]){if(i+1>=size){out[0]=0;return 0;}out[i]=in[i];i++;}out[i]=0;return 1;
}
static void tt_capture_course(u32 page,u32 source,u32 slot){
 tt_selected_clear();tt_selected_count++;tt_selected_status=1;
 u32 engine=W(0x1018a18cu,0),heaps=engine?W(engine,0xc):0;
 if(!heaps||W(heaps,0)<=3||!W(heaps,4))return;
 u32 common=W(W(heaps,4),12),data=common?W(common,0x28):0;
 if(!data||!W(0x1030c010u,0)||W(data,0x1438)!=1){tt_selected_status=2;return;}
 u32 native=W(source,0xf4),cup=12;
 for(u32 i=0;i<12;i++)if(W(data,i*0x80+slot*0x10)==native){cup=i;break;}
 if(cup==12){tt_selected_status=3;return;}
 tt_selected_name_message=W(data,cup*0x80+slot*0x10+8);
 tt_selected_prefix_message=W(data,cup*0x80+slot*0x10+4);
#ifdef ENABLE_TT_GHOST_SCOPE
 tt_capture_preview(source);
#endif
 u32 cup_page=W(page,0x37c);const char *directory=0;
 tt_selected_native_course=native;tt_selected_page=cup_page;tt_selected_slot=slot;
 if(!cup_page){
  if(native>=80){tt_selected_status=4;return;}
  directory=TT_CAPTURE_STRING(W(0x103028e8u,native*4));
 }else{
  u32 manager=W(0x10302564u,0),count=manager?W(manager,4):0,rows=manager?W(manager,8):0;
  if(!rows||count>256){tt_selected_status=5;return;}
  for(u32 i=0;i<count;i++){
   u32 row=rows+i*0x54;
   if(W(row,0)==cup_page&&W(row,4)==cup){directory=TT_CAPTURE_STRING(W(row,0x34+slot*4));tt_selected_name_message=W(row,0x14+slot*4);tt_selected_prefix_message=W(row,0x24+slot*4);break;}
  }
 }
 if(!directory||!tt_selected_copy(tt_selected_directory,sizeof tt_selected_directory,directory)){tt_selected_status=6;return;}
 if(!ctgp_tt_select(&tt_selected_category,ctgp_tt_tracks,CTGP_TT_TRACK_COUNT,
      tt_selected_directory,W(0x1030c000u,0),!!pink_enabled)){tt_selected_status=7;return;}
 const struct CtgpTTTrack *track=tt_selected_category.track;
 if(!tt_selected_copy(tt_selected_identity,sizeof tt_selected_identity,track->id)||
    !tt_selected_copy(tt_selected_revision,sizeof tt_selected_revision,track->revision)||
    !ctgp_tt_path(&tt_selected_category,tt_selected_path,sizeof tt_selected_path)){tt_selected_status=8;tt_selected_clear();return;}
 tt_selected_valid=1;tt_selected_status=9;
}
void tt_course_event(u32 page,u32 event){
 /* This native handler is called only after CTGP's transition/input filter.
  * Pointer equality targets the four course buttons, excluding cup arrows. */
 if(page&&event&&W(page,4)==44&&W(event,8)&&W(event,0x14)==2){
  u32 source=W(event,8);
  for(u32 slot=0;slot<4;slot++)if(W(page,0x274+slot*4)==source){tt_capture_course(page,source,slot);break;}
 }
 original_tt_course_event(page,event);
}
