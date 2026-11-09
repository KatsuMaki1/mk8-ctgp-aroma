/* Use the original GhostScrollList controls, replacing only its NEX fetch states
 * in the local prototype. Production authentication/transport is not emulated. */
#ifdef ENABLE_TT_LOCAL_ADAPTER
#include "tt_board_cache.h"
#endif
extern void original_tt_online_enter(u32);
extern void original_tt_online_calc(u32);
extern void original_tt_online_event(u32,u32);
extern void original_tt_online_exit(u32);
#ifdef ENABLE_TT_LOCAL_ADAPTER
static u8 tt_board_data[TT_BOARD_BYTES] __attribute__((aligned(64)));
static u8 tt_board_client[0x1700] __attribute__((aligned(64)));
static u8 tt_board_command[0xa80] __attribute__((aligned(64)));
static u32 tt_board_tick,tt_board_sequence,tt_board_count,tt_board_loaded;
static u32 selected_country(void); /* Options country (country_options.h): the development adapter's rows belong to that player */
volatile u32 tt_online_cache_reads,tt_online_cache_errors,tt_online_ui_updates;
static int tt_board_read(void){
 u32 add=settings_import(0x23b143c),init=settings_import(0x23b1444),open=settings_import(0x26cb59c),read=settings_import(0x26cb8d8),close=settings_import(0x249f5dc),del=settings_import(0x2714af8);
 if(!add||!init||!open||!read||!close||!del)return 0;
 if(FN(add,int(*)(void*,u32))(tt_board_client,0)<0)return 0;
 FN(init,void(*)(void*))(tt_board_command);int handle=0,result=-1;
 if(FN(open,int(*)(void*,void*,const char*,const char*,int*,u32))(tt_board_client,tt_board_command,"/vol/external01/ctgp-local-board.bin","r",&handle,0)>=0){
  result=FN(read,int(*)(void*,void*,void*,u32,u32,int,u32,u32))(tt_board_client,tt_board_command,tt_board_data,1,TT_BOARD_BYTES,handle,0,0);
  FN(close,int(*)(void*,void*,int,u32))(tt_board_client,tt_board_command,handle,0);
 }
 FN(del,int(*)(void*,u32))(tt_board_client,0);
 tt_online_cache_reads++;
 return result==TT_BOARD_BYTES&&tt_board_valid(tt_board_data,tt_selected_identity,tt_selected_revision,tt_selected_category.cc,tt_selected_category.pink);
}
static void tt_online_apply(u32 page){
 if(!tt_board_read()){tt_online_cache_errors++;return;}
 u32 sequence=tt_board_word(tt_board_data+20);
 if(tt_board_loaded&&sequence==tt_board_sequence)return;
 u32 rows=W(page,0x220),capacity=W(page,0x21c);if(!rows||capacity<57||capacity>64)return;
 tt_board_count=tt_board_word(tt_board_data+16);
 for(u32 i=0;i<57;i++){
  u32 row=W(rows,i*4);if(!row)continue;
  W(row,0)=W(row,4)=W(row,8)=0;B(row,0xc)=B(row,0xd)=0;
  for(u32 j=0;j<42;j++)B(row,0x38+j)=0;
  if(i<tt_board_count){
   const u8 *in=tt_board_data+256+i*256;
   FN(0x02595930u,void(*)(u32,u32,u32,u32,u32))(row,tt_board_word(in+4),tt_board_word(in),selected_country(),0); /* row+0xC = country id drawn as the flag by 02597374 */
   /* Row icon: 025959F8 expects an icon image buffer (0x2582C bytes), NOT 96-byte Mii store data; passing store
    * data crashes the icon builder (027ACB4C). Without a buffer the native list draws a blank icon. */
   W(row,4)=1; /* Native score row, no unimplemented NEX download action. */
   for(u32 j=0;j<40;j++)B(row,0x38+j)=in[32+j];
  }
 }
 tt_board_sequence=sequence;tt_board_loaded=1;tt_online_ui_updates++;
 FN(0x02597960u,void(*)(u32))(W(page,0x1cc));
}
#endif
/* Title part L_Title_00: a child control of the page (child array = page+0x28), identified by its
 * secondary vtable 0x100D8DE8 at +0x54 and owner page at +4; panes T_Title_00 / T_Title_01 are at
 * +0xAC / +0xB0 (verified in a live Cemu process, P24). P23 used page+0x1CC, the list control, and crashed. */
#ifndef TT_GUEST_PTR_OK
#define TT_GUEST_PTR_OK(p) ((p)>=0x10000000u&&(p)<0x60000000u)
#endif
static u32 tt_online_title_control(u32 page){
 u32 list=W(page,0x28),count=W(page,0x20);if(!TT_GUEST_PTR_OK(list)||count>128)return 0;
 for(u32 i=0;i<count;i++){
  u32 control=W(list,i*4);
  if(TT_GUEST_PTR_OK(control)&&W(control,0x54)==0x100d8de8u&&W(control,4)==page)return control;
 }
 return 0;
}
static void tt_title_write(u32 control){
 u32 name=W(control,0xac),prefix=W(control,0xb0);
 if(TT_GUEST_PTR_OK(name)&&tt_selected_name_message)FN(0x02536848u,void(*)(u32,u32,u32))(control,name,tt_selected_name_message);
 if(TT_GUEST_PTR_OK(prefix)){
  u32 show=tt_selected_prefix_message&&tt_selected_prefix_message!=0xffffffffu;
  FN(0x02531bdcu,void(*)(u32,u32,u32))(control,prefix,show);
  if(show)FN(0x02536848u,void(*)(u32,u32,u32))(control,prefix,tt_selected_prefix_message);
 }
}
static void tt_online_title(u32 page){
 if(!tt_selected_valid)return;
 u32 control=tt_online_title_control(page);if(control)tt_title_write(control);
}
/* The native title method 02596E3C(list, titleControl, arg) rewrites the donor course name whenever it runs
 * (P25 showed "Mario Kart Stadium" although the control and message were right), so override right after it. */
extern void original_tt_title_update(u32,u32,u32);
volatile u32 tt_title_native_calls,tt_title_overrides;
void tt_title_update(u32 self,u32 control,u32 arg){
 original_tt_title_update(self,control,arg);
 tt_title_native_calls++;
 if(!tt_ghost_active()||!tt_selected_valid||!TT_GUEST_PTR_OK(control)||W(control,0x54)!=0x100d8de8u)return;
 tt_title_write(control);tt_title_overrides++;
}
void tt_online_enter(u32 page){
 if(tt_category_active()&&!tt_ghost_active())tt_scope_prepare();
 original_tt_online_enter(page);
 if(!tt_ghost_active())return;
#ifdef ENABLE_TT_LOCAL_ADAPTER
 tt_online_requests++;tt_board_tick=0;tt_board_loaded=0;tt_board_count=0;
 W(page,0x200)=7;W(page,0x204)=13;W(page,0x208)=0;B(page,0x231)=0;
 FN(0x02597960u,void(*)(u32))(W(page,0x1cc));
 tt_online_apply(page);
#endif
 tt_online_title(page);
}
void tt_online_calc(u32 page){
 if(tt_category_active()&&!tt_ghost_active())tt_scope_prepare();
#ifdef ENABLE_TT_LOCAL_ADAPTER
 if(!tt_ghost_active()){original_tt_online_calc(page);return;}
 if(!(tt_board_tick++%120))tt_online_apply(page);
#else
 /* The native NEX service is now available. Preserve its list state machine,
  * input transitions and sounds; only replace the selected course title. */
 original_tt_online_calc(page);
#endif
 if(tt_ghost_active())tt_online_title(page);
}
void tt_online_event(u32 page,u32 event){
#ifdef ENABLE_TT_LOCAL_ADAPTER
 if(!tt_ghost_active()){original_tt_online_event(page,event);return;}
 if(!event||!W(event,8))return;
 u32 action=W(event,0xc);
 if(action==0x33){tt_scope_reload_pending=1;W(page,0x80)=0x19;FN(0x0253f048u,void(*)(u32,u32))(page,page+0xd8);}
#else
 original_tt_online_event(page,event);
#endif
}
void tt_online_exit(u32 page){
#ifdef ENABLE_TT_LOCAL_ADAPTER
 if(!tt_category_active())original_tt_online_exit(page);
#else
 original_tt_online_exit(page);
#endif
}
