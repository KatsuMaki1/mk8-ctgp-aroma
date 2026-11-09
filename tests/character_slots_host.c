#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <stdarg.h>
typedef unsigned int u32;
static u32 *host_word(u32,u32);
static unsigned char *host_byte(u32,u32);
static void *host_function(u32);
#define W(p,o) (*host_word((u32)(p),(o)))
#define B(p,o) (*host_byte((u32)(p),(o)))
#define FN(a,t) ((t)host_function(a))
#define ROB_PRIVATE_VOICE 1
#include "../tools/native/character_slots.c"
static u32 memory[0x20000/4],zero,engine_word,original_names,configured,private_prefix,recipe_id;
static char routed_prefix[128];
static u32 menu_voice_driver;
void original_char_menu_voice(u32 actor,u32 narrator){(void)narrator;menu_voice_driver=W(actor,0x7c);}
static u32 fallback_driver;
u32 previous_char_vehicle_icon(u32 o,u32 k,u32 id,const u32 *d,u32 c){(void)o;(void)k;(void)c;fallback_driver=d?*d:0xffffffffu;return id+100;}
static u32 *host_word(u32 p,u32 o) {
    u32 address=p+o,base=(u32)(uintptr_t)buttons;
    if(address>=base && address-base<sizeof(buttons))return (u32*)((unsigned char*)buttons+(address-base));
    if(address==0x1018a18c)return &engine_word;
    if(address==0x10206328)return &zero;
    assert(address<sizeof(memory) && !(address&3));return &memory[address/4];
}
static unsigned char *host_byte(u32 p,u32 o) {
    u32 a=p+o;assert(a<sizeof(memory));return (unsigned char*)memory+a;
}
static void clear_navigation(u32 control){W(control,0xec)=0;}
static void add_navigation(u32 control,u32 button){
    u32 count=W(control,0xec);assert(count<W(control,0xe4));
    W(W(control,0xe8),count*4)=button;W(button,0x44)=count;W(control,0xec)=count+1;
}
static void display_name(u32 page,u32 player,const unsigned short *text){
    (void)page;assert(player==2);assert(text[0]=='R' && text[5]=='.' && !text[6]);
}
static u32 driver_id(u32 driver){return W(driver,0);}
static u32 player_context(u32 object){(void)object;return 2;}
static u32 player_index(u32 object){return object;}
static u32 load_icon(u32 resource,const struct NativeString *name){
    assert(resource==0x1a400);
    if(!strcmp(name->text,"ui/cmn/a_menu/timg/ct_ROB_K_Std^q.bflim"))return 0xc001;
    if(!strcmp(name->text,"ui/cmn/a_menu/timg/ct_ROB_K_Skl^q.bflim"))return 0xc002;
    if(!strcmp(name->text,"ui/cmn/a_menu/timg/ct_ROB_B_Std^q.bflim"))return 0xc003;
    if(!strcmp(name->text,"ui/cmn/a_menu/timg/ct_ROB_V_Atv^q.bflim"))return 0xc004;
    if(!strcmp(name->text,"ui/cmn/a_menu/timg/tc_KP_G_Std_Mtn^q.bflim"))return 0xc100;
    if(!strcmp(name->text,"tc_KP_K_Ufo^q.bflim"))return 0xc101;
    return 0;
}
static void bind_voice(u32 list,const char *name,u32 heap,u32 a,u32 b){
    assert(!strcmp(name,"ROB"));assert(!heap && !a && !b);W(list,4)++;
}
static unsigned final_model_paths;
static void format_voice_path(u32 out,const char *format,...){
    (void)out;assert(!strcmp(format,"%s"));
    va_list args;va_start(args,format);const char *path=va_arg(args,const char*);va_end(args);
    if(!strcmp(path,"custom/characters/ROB/driver/ROB.bfres"))final_model_paths++;
}
static void *host_function(u32 address){
    if(address==0x0253d47c)return (void*)load_icon;
    if(address==0x021b6e38)return (void*)player_context;
    if(address==0x02441d48)return (void*)player_index;
    if(address==0x021941a8)return (void*)driver_id;
    if(address==0x02056834)return (void*)bind_voice;
    if(address==0x02740e1c)return (void*)format_voice_path;
    if(address==0x02537680)return (void*)clear_navigation;
    if(address==0x0253783c)return (void*)add_navigation;
    if(address==0x025d25b0)return (void*)display_name;
    abort();
}
void original_char_create(u32 page) {
    u32 array=character_button_array(page);
    for(u32 i=0;i<37;i++)W(array,i*4)=0x5000+i*0x200;
}
void original_char_setup(u32 page){
    W(page,0xac)=0x3000;W(0x3000,0xe4)=37;W(0x3000,0xe8)=0x3200;W(0x3000,0xec)=36;W(0x3000,0xe0)=0x3400;
}
void original_char_available(u32 page,u32 *out,const u32 *id){(void)page;*out=*id>=30?4:5;}
void original_char_button(u32 button,const u32 *id,const u32 *state){(void)state;W(button,0xf8)=*id;configured++;}
u32 original_char_icon(u32 loader,const u32 *id,u32 variant){(void)loader;assert(!variant);return *id;}
void original_char_name(u32 page,u32 player,const u32 *id,u32 variant){(void)page;(void)player;(void)id;(void)variant;original_names++;}
static char sound_label[88];
u32 original_char_sound_lookup(u32 a,u32 o,const char *l){(void)a;(void)o;if(l)strcpy(sound_label,l);return 0x1234;}
void original_char_horn_label(u32 a){(void)a;}
u32 original_char_menu_play(u32 a,const char *l){(void)a;(void)l;return 0x5678;}
void original_char_audio_init(u32 a){(void)a;}
void original_char_texture_name(u32 l,u32 out,const u32 *kind,const u32 *id,u32 variant){(void)l;(void)out;(void)kind;(void)id;(void)variant;}
void original_char_finalise(u32 object,u32 parameters){
    (void)parameters;assert(W(object,0)==28);character_prefix(object,"driver/",0);assert(private_prefix);
}
void previous_char_recipe(u32 object,u32 parameters,const u32 *source){
    (void)parameters;recipe_id=source[0];assert(source[3]==41 && source[6]==22);
    character_prefix(object,"driver/",0);
}
void previous_char_prefix(u32 object,const char *prefix,u32 source){
    (void)object;(void)source;private_prefix=!strcmp(prefix,"custom/characters/ROB/driver/");strcpy(routed_prefix,prefix);
}
int main(void){
    W(0x15000,0x7c)=28;rob_menu_selected[2]=1;character_menu_voice(0x15000,0);
    assert(menu_voice_driver==37 && W(0x15000,0x7c)==28);
    rob_menu_selected[2]=0;character_menu_voice(0x15000,0);
    assert(menu_voice_driver==28 && W(0x15000,0x7c)==28);
    W(0x18f00,0)=0x19000;strcpy((char*)memory+0x19000,"BodyK_Std_Mtn_Alb");
    rob_recipe_scope=1;character_prefix(0,"kart/body_tex/",0x18f00);
    assert(!strcmp(routed_prefix,"custom/characters/ROB/kart/body_tex/"));
    rob_recipe_scope=0;character_prefix(0,"kart/body_tex/",0x18f00);
    assert(!strcmp(routed_prefix,"kart/body_tex/"));
    rob_recipe_scope=1;strcpy((char*)memory+0x19000,"BodyB_Jet_Mtn_Alb");character_prefix(0,"kart/body_tex/",0x18f00);
    assert(!strcmp(routed_prefix,"kart/body_tex/"));rob_recipe_scope=0;
    u32 rob_driver=37,morton=28;
    assert(character_vehicle_icon(0,0,39,&rob_driver,0)==139 && fallback_driver==28);
    engine_word=0x1a000;W(0x1a000,12)=0x1a100;W(0x1a100,0)=5;W(0x1a100,4)=0x1a200;
    W(0x1a200,16)=0x1a300;W(0x1a300,4)=0x1a400;
    assert(character_vehicle_icon(0,0,0,&rob_driver,0)==0xc001);
    assert(character_vehicle_icon(0,0,1,&rob_driver,0)==0xc002);
    assert(character_vehicle_icon(0,0,14,&rob_driver,0)==0xc003);
    assert(character_vehicle_icon(0,0,23,&rob_driver,0)==0xc004);
    assert(character_vehicle_icon(0,2,0,&rob_driver,0)==0xc100);
    assert(character_vehicle_icon(0,0,2,&rob_driver,0)==0xc101);
    assert(character_vehicle_icon(0,0,0,&morton,0)==100 && fallback_driver==28);
    engine_word=0;
    horn_for_rob=1;assert(character_sound_lookup(0,0,"pSE_HORN_ROB_ON")==0x1234);
    assert(!strcmp(sound_label,"pSE_HORN_MOR_ON"));
    character_sound_lookup(0,0,"pSE_HORN_K_SKL");assert(!strcmp(sound_label,"pSE_HORN_K_SKL"));
    horn_for_rob=0;character_sound_lookup(0,0,"pSE_HORN_MOR_ON");assert(!strcmp(sound_label,"pSE_HORN_MOR_ON"));
    assert(character_menu_play(0,"pVO_M_ROB_SELECT_CHAR")==0x5678);
    W(0x16000,0x20c)=0x17000;W(0x17000,0)=28;W(0x16000,0x218)=5;
    character_audio_init(0x16000);assert(W(0x16000,0x218)==5);
    W(0x17000,0)=37;character_audio_init(0x16000);
    assert(W(0x16000,0x218)==6 && character_voice_bank_state[1]==5 && character_voice_bank_state[2]==6);
    u32 page=0x1000;W(page,0x38c)=0xabcdef01;character_create(page);
    assert(W(page,0x38c)==0xabcdef01);
    for(u32 i=0;i<36;i++)assert(W(page,0x2fc+i*4)==0x5000+i*0x200);
    character_setup(page);assert(W(0x3000,0xec)==37 && W(0x3400,8)==6 && configured==37);
    u32 array=character_button_array(page),rob=W(array,144);
    assert(W(rob,0xf8)==37 && B(rob,0xf4)==1 && W(rob,0x44)==36);
    assert(W(W(array,28*4),0xf8)==28);
    assert(B(W(array,30*4),0xf4)==0); /* Native DLC lock is retained. */
    u32 id=37;assert(character_icon(0,&id,0)==28);
    character_name(page,2,&id,0);id=0;character_name(page,2,&id,0);assert(original_names==1);
    u32 source[9]={37,0,0,41,0,0,22,0,0},snapshot[9];memcpy(snapshot,source,sizeof(source));
    character_recipe(0,0,source);assert(recipe_id==28 && private_prefix && !memcmp(source,snapshot,sizeof(source)));
    character_prefix(0,"driver/",0);assert(!private_prefix); /* Scope restored. */
    source[0]=0;character_recipe(0,0,source);assert(recipe_id==0 && !private_prefix);
    W(0x1800,0)=37;character_finalise(0x1800,0);assert(W(0x1800,0)==37 && !rob_recipe_scope && final_model_paths==1);
    W(0x1900,0)=0x1a00;W(0x1900,8)=64;u32 kind=2;id=37;
    character_texture_name(0,0x1900,&kind,&id,0);
    assert(!strcmp((char*)memory+0x1a00,"ui/cmn/a_common/timg/tc_MapChara_ROB^l.bflim"));
    return 0;
}
