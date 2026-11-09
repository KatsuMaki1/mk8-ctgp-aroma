#include <assert.h>
#include <stdint.h>
#include <stdio.h>
typedef uint32_t u32;typedef unsigned char u8;
struct Category{u32 cc,pink;};
static struct Category tt_selected_category={200,0};
static char tt_selected_identity[]="ct.test",tt_selected_revision[]="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
static u32 tt_selected_valid=1,tt_selected_name_message=5014,tt_selected_prefix_message=0xffffffffu;
static u32 title_message,title_pane,prefix_visible;
static u32 tt_online_requests,tt_scope_reload_pending,active=1,forwarded,transitions,last_page,last_flow;
static u32 memory[4096];
#define W(p,o) memory[((p)+(o))/4]
#define B(p,o) ((u8*)memory)[(p)+(o)]
static u32 settings_import(u32 address){(void)address;return 0;}
static int tt_ghost_active(void){return active;}
static int tt_category_active(void){return active;}
static void tt_scope_prepare(void){}
static void transition(u32 page,u32 flow){transitions++;last_page=page;last_flow=flow;}
static void set_title(u32 control,u32 pane,u32 message){(void)control;title_message=message;title_pane=pane;}
static void show_prefix(u32 control,u32 pane,u32 visible){(void)control;(void)pane;prefix_visible=visible;}
static void *dispatch(u32 address){if(address==0x02536848)return (void*)set_title;if(address==0x02531bdc)return (void*)show_prefix;assert(address==0x0253f048);return (void*)transition;}
#define FN(a,t) ((t)dispatch(a))
#define TT_GUEST_PTR_OK(p) ((p)>=0x100u&&(p)<0x4000u)
static u32 selected_country(void){return 160;}
#define ENABLE_TT_LOCAL_ADAPTER
#include "../tools/native/tt_online_ui.h"
void original_tt_online_enter(u32 page){(void)page;}
static u32 native_title_calls;void original_tt_title_update(u32 a,u32 b,u32 c){(void)a;(void)b;(void)c;native_title_calls++;}
void original_tt_online_calc(u32 page){(void)page;}
void original_tt_online_exit(u32 page){(void)page;}
void original_tt_online_event(u32 page,u32 event){(void)page;(void)event;forwarded++;}
int main(void){
 u32 page=0x1000,event=0x2000;W(event,8)=1;W(event,0xc)=0x33;
 W(event,0x14)=0;tt_online_event(page,event);assert(transitions==1&&last_page==page&&last_flow==page+0xd8&&W(page,0x80)==0x19&&tt_scope_reload_pending);
 W(event,0x14)=2;tt_online_event(page,event);assert(transitions==2);
 W(event,8)=0;tt_online_event(page,event);assert(transitions==2);
 /* Child array at page+0x28: a list control (wrong class) first, then the title control. */
 W(page,0x20)=2;W(page,0x28)=0x2800;W(0x2800,0)=0x2900;W(0x2900,0x54)=0x100d8e00u;W(0x2900,4)=page;
 W(0x2800,4)=0x3000;W(0x3000,0x54)=0x100d8de8u;W(0x3000,4)=page;W(0x3000,0xac)=0x3100;W(0x3000,0xb0)=0x3200;
 tt_online_title(page);assert(title_message==5014&&title_pane==0x3100&&!prefix_visible);
 title_message=0;W(0x3000,4)=0x9999; /* owned by another page: never touched */
 tt_online_title(page);assert(title_message==0);
 W(page,0x28)=0;tt_online_title(page);assert(title_message==0);
 title_message=0;tt_title_update(0x5000,0x3000,0);assert(native_title_calls==1&&title_message==5014&&tt_title_overrides==1);
 title_message=0;tt_title_update(0x5000,0x2900,0);assert(title_message==0&&tt_title_overrides==1); /* other class: untouched */
 active=0;tt_title_update(0x5000,0x3000,0);assert(title_message==0);
 active=1;active=0;tt_online_event(page,event);assert(forwarded==1);
 puts("B input uses the traced native Ghost return flow for key and touch events; inactive mode stays native");
}
