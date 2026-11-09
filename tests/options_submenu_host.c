#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
static struct{uint32_t a,v;} words[2048];static unsigned used;
static uint32_t *word(uint32_t a){for(unsigned i=0;i<used;i++)if(words[i].a==a)return &words[i].v;assert(used<2048);words[used].a=a;return &words[used++].v;}
#define W(p,o) (*word((p)+(o)))
#define B(p,o) (*((unsigned char*)word(((p)+(o))&~3u)+(((p)+(o))&3u)))
static void *host_native(uint32_t);
#define FN(a,t) ((t)host_native(a))
#include "../tools/native/options_submenu.c"
static unsigned transitions,finishes,forwarded,modes,sounds;
static unsigned message_assignments;
void original_language_set_default(u32 c,u32 id){(void)c;(void)id;message_assignments++;}
void original_language_set_named(u32 c,const struct String *n,u32 id){(void)c;(void)n;(void)id;message_assignments++;}
void original_language_set_pane(u32 c,u32 n,u32 id){(void)c;(void)n;(void)id;message_assignments++;}
void original_language_page_calc(u32 p){(void)p;}
static u32 nop(void){return 0;}
static void transition(void){transitions++;}
static void finish(void){finishes++;}
static void sound(void){sounds++;}
static unsigned int context(void){return 0xa000;}
static int slot(unsigned int e){return e==0x8300?0:-1;}
static void native_focus(u32 manager,u32 controller,u32 target,u32 a,u32 b){(void)a;(void)b;if(manager)W(manager,0xc+controller*0x28)=target;}
static void *host_native(uint32_t a){if(a==0x25382bc)return native_focus;if(a==0x24ce59c)return context;if(a==0x24d4b20)return slot;if(a==0x2048798)return sound;if(a==0x253f048)return transition;if(a==0x2579470)return finish;return nop;}
void original_sub_top_create(u32 p){(void)p;}
void original_sub_top_event(u32 p,u32 e){(void)p;(void)e;forwarded++;}
void original_sub_enter(u32 p){(void)p;}
void original_sub_calc(u32 p){(void)p;}
void original_sub_create(u32 p){(void)p;}
const char *original_language_code(void){return "ef";}
static const u16 fallback_message[]={0};
const u16 *original_language_message(u32 manager,u32 id){(void)manager;return id==0xffffffff?0:fallback_message;}
u32 original_country_get(u32 p,u32 i){(void)p;return 49+i;}
u32 original_country_local_get(u32 m,u32 e){int i=slot(e);return i>=0&&i<4?B(m,0x80+i):0;}
void previous_mode_event(u32 p,u32 e){(void)p;(void)e;modes++;}
u32 original_flag_texture(u32 owner,u32 id){return owner+id;}
void original_set_visible_trace(u32 control,u32 pane,u32 visible){(void)control;(void)pane;(void)visible;}
void original_anim_frame_trace(double f,u32 array,u32 index){(void)f;(void)array;(void)index;}
u32 original_globe_plate(u32 a,u32 b,u32 c,u32 d,u32 e,u32 f,u32 g,u32 h){(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)g;(void)h;return 0;}
int main(void){u32 p=0x1000,e=0x6000;W(p,4)=25;W(e,0)=p+0x230;
 W(e,0x1c)=8;sub_top_event(p,e);assert(transitions==0&&forwarded==1);
 W(e,0x1c)=0x200;sub_top_event(p,e);assert(transitions==1&&options==1&&W(p,0xdc)==28);
 W(e,8)=1;W(e,0xc)=13;W(e,0x14)=2;sub_top_event(p,e);assert(transitions==2&&sounds==2);
 W(p,0x100)=0x2000;W(0x2000,200)=0x2100;W(p,0x20)=1;W(p,0x28)=0x4000;W(0x4000,0)=0x3000;W(0x3000,0)=0;button0=0x3000;W(0x10305000,0)=1;
 W(e,8)=1;W(e,0xc)=0;W(e,0x14)=2;sub_mode_event(p,e);assert(W(0x10305000,0)==0&&pending==3&&modes==0);
 sub_mode_event(p,e);assert(W(0x10305000,0)==0);/* no duplicate decide while completing */
 sub_calc(p);sub_calc(p);assert(finishes==0);sub_calc(p);assert(finishes==1&&pending==0);
 sub_mode_event(p,e);assert(W(0x10305000,0)==1&&pending==3);
 W(e,8)=0;W(e,0x1c)=4;sub_mode_event(p,e);assert(options==0&&pending==0&&modes==1);
 W(0xa000,0x2b8)=0x7000;W(0x7000,0x34)=3;W(0x7000,0x3c)=0x8000;
 W(0x8000,0)=0x8100;W(0x8000,4)=0x8200;W(0x8000,8)=0x8300;
 W(0x8100,0x3c)=1;W(0x8200,0x3c)=2;W(0x8300,0x3c)=3;
 B(0x7000,0x74)=77;B(0x7000,0x75)=3;B(0x7000,0x80)=77;B(0x7000,0x81)=18;B(0x7000,0x82)=0;B(0x7000,0x83)=0;
 B(0x8200,0x9c8)=49;B(0x8300,0x9c8)=77;
 country_choice=0;assert(country_get(0x7000,0)==49);assert(country_local_get(0x7000,0x8300)==77);
 country_choice=2;assert(selected_country()==67);country_apply();
 assert(B(0x7000,0x74)==77&&B(0x7000,0x75)==3&&B(0x7000,0x80)==77&&B(0x7000,0x81)==18); /* Country selection must not overwrite player/controller bytes. */
 assert(country_get(0x7000,0)==49&&country_get(0x7000,1)==50&&country_get(0x7000,2)==51&&country_get(0x7000,3)==52);
 assert(B(0x8200,0x9c8)==49&&B(0x8300,0x9c8)==77);
 assert(country_local_get(0x7000,0x8300)==77&&country_local_get(0x7000,0x8200)==0);
 country_choice=0;country_apply();assert(B(0x7000,0x74)==77&&B(0x7000,0x75)==3&&B(0x7000,0x80)==77&&B(0x7000,0x81)==18);
 assert(B(0x8200,0x9c8)==49&&B(0x8300,0x9c8)==77);
 options=1;pending=0;country_choice=0;button1=0x3100;W(e,8)=1;W(e,0xc)=1;W(e,0x14)=2;sub_mode_event(p,e);assert(country_choice==1&&pending==3&&last_focus==1&&decided_button==0x3100);
 /* Horizontal events cycle the focused option without a decide/transition. */
 pending=0;last_focus=1;country_choice=0;W(e,8)=0;W(e,0x1c)=0x80;
 sub_mode_event(p,e);assert(country_choice==COUNTRY_COUNT-1&&pending==0);
 W(e,0x1c)=0x100;sub_mode_event(p,e);assert(country_choice==0);
 W(e,0x1c)=0x180;sub_mode_event(p,e);assert(country_choice==0);
 last_focus=2;language_choice=0;W(e,0x1c)=0x100;sub_mode_event(p,e);
 assert(language_choice==1&&language_index()==0&&language_code()[1]=='e');
 assert(language_message(1,0xffffffff)==0);
 for(u32 i=0;i<LANGUAGE_COUNT;i++){
  language_choice=i+1;assert(language_index()==i);
  for(u32 j=0;j<languages[i].count;j++)assert(language_message(1,languages[i].messages[j].id)==languages[i].messages[j].text);
 }
 language_choice=0;assert(language_index()==1&&language_message(1,0x899)==fallback_message);
 /* The native row model keeps labels and values in different text panes. */
 assert(model_type(&option_models[0])==5&&model_enabled(&option_models[0])==1);
 assert(model_label(&option_models[1])==languages[1].country);
 assert(model_value(&option_models[1])[0]==languages[1].automatic[0]);
 u32 dir=2;country_choice=0;model_change(&option_models[1],&dir);assert(country_choice==COUNTRY_COUNT-1);
 dir=3;model_change(&option_models[1],&dir);assert(country_choice==0);
 u32 oldspeed=W(0x10305000,0);model_change(&option_models[0],&dir);assert(W(0x10305000,0)==(oldspeed^1));
 language_choice=0;model_change(&option_models[2],&dir);assert(language_choice==1);
 dir=2;model_change(&option_models[2],&dir);assert(language_choice==0);
 for(u32 l=0;l<LANGUAGE_COUNT;l++)for(u32 c=0;c<COUNTRY_COUNT;c++){
  language_choice=l+1;country_choice=c;const u16 *value=model_value(&option_models[1]);u32 size=0;
  while(value[size]){assert(value[size]!='\n');size++;assert(size<=27);}
 }
 language_choice=0;country_choice=0;
 /* Hidden Options must have no input/update entries or side effects in Solo. */
 row_owner=p;option_rows[0]=0x9100;option_rows[1]=0x9200;option_rows[2]=0x9300;
 if(OPTION_ROW_COUNT==4){option_rows[3]=0x9380;options=1;pink_enabled=0;model_change(&option_models[3],&dir);assert(pink_enabled==1);model_change(&option_models[3],&dir);assert(pink_enabled==0);}
 row_page_count=4;row_page_end=4+OPTION_ROW_COUNT;row_nav_count=4;row_nav_end=4+OPTION_ROW_COUNT;W(p,0xac)=0x9400;
 rows_active(p,1);assert(W(p,0x20)==4+OPTION_ROW_COUNT&&W(0x9400,0xec)==4+OPTION_ROW_COUNT);
 W(0x9400,0xc)=3+OPTION_ROW_COUNT; /* Actual captured regression: focus6 with Solo count4. */
 rows_active(p,0);assert(W(p,0x20)==4&&W(0x9400,0xec)==4);
 assert(W(0x9400,0xc)==0);
 options=0;u32 previous_choice=country_choice;model_change(&option_models[1],&dir);assert(country_choice==previous_choice);
 W(0xa000,0x2d0)=0xb000;W(0xb000,4)=2;W(0xb000,8)=3;
 language_set(1);assert(W(0xb000,8)==1);language_set(0);assert(W(0xb000,8)==3&&W(0xb000,4)==2);
 /* Refresh live message-bound controls once per language epoch. Stale/layout-
  * replaced controls are ignored, without dereferencing saved pane pointers. */
 language_binding_count=0;W(p,0x20)=1;W(p,0x28)=0x4000;W(0x4000,0)=0x3000;
 W(0x3000,4)=p;W(0x3000,0x50)=0x3500;
 language_set_default(0x3000,0x899);unsigned assigned=message_assignments;
 language_set(1);language_page_calc(p);assert(message_assignments==assigned+1);
 language_page_calc(p);assert(message_assignments==assigned+1);
 W(0x3000,0x50)=0x3600;language_set(2);language_page_calc(p);assert(message_assignments==assigned+1);
 language_set(0);
 u32 russia=0;for(u32 i=0;i<COUNTRY_COUNT;i++)if(country_ids[i]==100)russia=1;
 assert(russia);
 puts("Native Options input, country boundaries, 8 language catalogs, message fallback and Auto passed");return 0;}
