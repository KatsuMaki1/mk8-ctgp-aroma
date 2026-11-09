typedef unsigned int u32;typedef unsigned short u16;typedef unsigned char u8;
#ifndef W
#define W(p,o) (*(volatile u32 *)((u32)(p)+(o)))
#define B(p,o) (*(volatile u8 *)((u32)(p)+(o)))
#endif
#ifndef FN
#define FN(a,t) ((t)(a))
#endif
struct String{const char *text;u32 vtable;};
extern void original_sub_top_create(u32);extern void original_sub_top_event(u32,u32);
extern void original_sub_enter(u32);extern void original_sub_calc(u32);
extern void original_sub_create(u32);
extern void previous_mode_event(u32,u32);
const char marker[]="MK8_OPTIONS_NATIVE_SUBMENU_V1";
volatile u32 pink_enabled=0; /* OFF by default; experiment is opt-in per session. */
#ifdef ENABLE_TT_CAPTURE
#include "tt_selection.h"
#endif
#ifdef ENABLE_TT_GHOST_SCOPE
#include "tt_ghost_scope.h"
#include "tt_online_ui.h"
#endif
static u32 options,pending,button0,button1,button2,last_focus,decided_button,top_page;
static u32 pane(u32 c,const char *s){struct String n={s,0x100e10f8};return FN(0x2531718,u32(*)(u32,const struct String*))(c,&n);}
static void visible(u32 c,const char*s,u32 v){u32 p=pane(c,s);if(p)FN(0x2531bdc,void(*)(u32,u32,u32))(c,p,v);}
#ifdef ENABLE_TT_RED_BACKGROUND
#include "tt_background.h"
#endif
#include "options_language.h"
#include "country_options.h"
/* nex_trace.h disabled: hooking the NEX dispatchers makes Worldwide matchmaking hang on "Searching for players" (P41-P44). Do not re-enable. */
static void settings_tick(void);
#include "options_message_cache.h"
#ifdef ENABLE_OPTIONS_STORE
#include "options_store.h"
#else
static void settings_changed(void){}
static void settings_save(void){}
static void settings_load(void){}
static void settings_tick(void){}
#endif
static void label(u32 c){const struct LocalLanguage *l=&languages[language_index()];option_text(c,l->speed,W(0x10305000,0)?l->on:l->off,0);}
static void focus(u32 p,u32 id);
static void refresh_top(void){
 static const u32 ids[]={0x835,0x837,0x83a,0x83b,0x83c,0x83d};
 if(!top_page)return;
 u32 count=W(top_page,0x20),array=W(top_page,0x28);if(count>128||!array)return;
 for(u32 i=0;i<count;i++){
  u32 c=W(array,4*i);if(!c)continue;u32 id=W(c,0);
  if(id<6)FN(0x25367ac,void(*)(u32,u32))(c,ids[id]);
 }
}
#include "options_rows.h"
void sub_create(u32 page){
 original_sub_create(page);
 /* Allocate and bind while the native page-creation heap is active. */
 create_rows(page,W(W(page,0x100),200));
 rows_active(page,0);
 update_rows(W(W(page,0x100),200),0);
}
static void focus(u32 p,u32 id){
 u32 target=options&&id<OPTION_ROW_COUNT&&option_rows[id]?W(option_rows[id],0x44):id;
 FN(0x25382bc,void(*)(u32,u32,u32,u32,u32))(W(p,0xac),0,target,0,1);
}
static void open(u32 p){FN(0x2048798,void(*)(u32))(0x100e1468);options=1;pending=0;W(p,0xdc)=28;FN(0x253a008,void(*)(u32,u32,u32))(p+0xd8,4,5);W(p,0x80)=25;FN(0x253f048,void(*)(u32,u32))(p,p+0xd8);}
void sub_top_create(u32 p){
 language_binding_count=language_page_count=0;original_sub_top_create(p);settings_load();if(W(p,4)!=25)return;top_page=p;
 options=0;pending=0;W(p,0x244)|=0x200;
 u32 count=W(p,0x20),old=W(p,0x28);if(count>128)return;
 if(count==W(p,0x24)){
  u32 a=FN(0x2721868,u32(*)(u32))((count+4)*4);if(!a)return;
  for(u32 i=0;i<count;i++)W(a,i*4)=W(old,i*4);
  W(p,0x28)=a;W(p,0x24)=count+4;
 }
 /* Same touch control as native footer shortcuts, with no + binding. */
 u32 c=FN(0x257b5fc,u32(*)(u32,u32))(0,0);if(!c)return;
 struct String name={"P_SettingsTouch_00",0x100e10f8};
 FN(0x253ecf4,void(*)(u32,u32,u32,const struct String*))(p,c,W(p,0x260),&name);
 W(c,0)=13;
 /* Rotate only the native + badge. Keep both images in the native animated tree. */
 u32 badge=pane(c,"P_PlusBtnIcon_00");if(badge)W(badge,0x30)=0x42340000u; /* Z=45 degrees */
}
void sub_top_event(u32 p,u32 e){
 settings_load();
 if(W(p,4)==25&&e){
  if(!W(e,8)&&W(e,0)==p+0x230&&(W(e,0x1c)&0x200)){open(p);return;}
  if(W(e,8)&&W(e,0xc)==13){if(W(e,0x14)==2)open(p);return;}
  if(W(e,8)&&W(e,0x14)==2)options=0;
 }
 original_sub_top_event(p,e);
}
static void arrange(u32 p){
 rows_active(p,options);
 u32 c=W(W(p,0x100),200);
 update_rows(c,options);
 visible(c,"N_GrandPrix_Sg_00",!options);visible(c,"N_Battle_Sg_00",!options);visible(c,"N_TimeAttack_Sg_00",!options);visible(c,"N_OriginalRule_Sg_00",!options);
 visible(c,"N_Movie_00",!options);visible(c,"T_CTGPOptions_00",options);
 u32 a=W(p,0x28),count=W(p,0x20);button0=button1=button2=0;
 for(u32 i=0;i<count;i++){u32 b=W(a,i*4);if(!b)continue;if(W(b,0)==0)button0=b;if(W(b,0)==1)button1=b;if(W(b,0)==2)button2=b;}
 for(u32 i=0;i<4;i++){
  u32 b=0;for(u32 j=0;j<count;j++){u32 candidate=W(a,j*4);if(candidate&&W(candidate,0)==i){b=candidate;break;}}
  if(!b)continue;
  W(b,0xd8)=options?0:p+0xc8;
  visible(b,"N_All_00",!options);
  if(options){if(i==2)language_label(b);else if(i==1)country_label(b);else if(!i)label(b);visible(b,"P_Img_00",0);}
  else{FN(0x25367ac,void(*)(u32,u32))(b,0x899+i);visible(b,"P_Img_00",1);}
 }

}
void sub_enter(u32 p){rows_active(p,options);original_sub_enter(p);arrange(p);last_focus=0;focus(p,0);}
void sub_calc(u32 p){
#ifdef ENABLE_TT_RED_BACKGROUND
 if(!options)tt_background_allowed=0;
#endif
 settings_tick();original_sub_calc(p);if(!options){if(p==row_owner)arrange(p);return;}
 arrange(p);
 if(pending&&!--pending){FN(0x2579470,void(*)(u32,int))(decided_button,0);focus(p,last_focus);}
}
void sub_mode_event(u32 p,u32 e){
 if(options&&e){
  if(W(e,8)){
   u32 id=W(e,0xc),kind=W(e,0x14);
   if(id>=14&&id<14+OPTION_ROW_COUNT){if(kind==0)last_focus=id-14;return;}
   if(id>2){if(kind==0)focus(p,last_focus);return;}
   if(kind==0)last_focus=id;
   if(kind==2){if(!pending){
    last_focus=id;decided_button=id==2?button2:(id?button1:button0);
    if(id==2){language_set(cycle_choice(language_choice,LANGUAGE_COUNT+1,1));refresh_top();}
    else if(id){country_choice=cycle_choice(country_choice,COUNTRY_COUNT,1);country_apply();country_label(button1);}
    else{W(0x10305000,0)^=1;label(button0);}
    settings_changed();pending=3;
   }return;}
   return;
  }
  /* Native repeated UI directions: D-pad and stick share these bits.
   * Consume horizontal input here, leaving vertical focus navigation native. */
  u32 horizontal=W(e,0x1c)&0x180;
  if(option_rows[0]&&horizontal)return; /* Native row owns repeat and arrow sound. */
  if(horizontal&&(last_focus==1||last_focus==2)){
   if(horizontal!=0x180&&!pending){
    int direction=horizontal==0x80?-1:1;
    if(last_focus==1){country_choice=cycle_choice(country_choice,COUNTRY_COUNT,direction);country_apply();}
    else{language_set(cycle_choice(language_choice,LANGUAGE_COUNT+1,direction));refresh_top();}
    settings_changed();FN(0x2048798,void(*)(u32))(0x100e1468);
   }
   return;
  }
  if(W(e,0x1c)&4){settings_save();options=0;pending=0;}
  else return;
 }
 previous_mode_event(p,e);
}

#ifdef ENABLE_PINK_DRIFT
#include "pink_drift.c"
#endif
