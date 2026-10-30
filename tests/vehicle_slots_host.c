#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned int u32;typedef unsigned char u8;
static unsigned char mem[0x100000];
#define W(p,o) (*(u32*)(mem+(((u32)(p)+(o))&0xfffff)))
#define B(p,o) (*(u8*)(mem+(((u32)(p)+(o))&0xfffff)))
static void *resolve(u32);
#define FN(a,t) ((t)resolve(a))
struct NativeString {const char *text;u32 vtable;};
static u32 menu_heap;
static u32 heap_at(u32 i){return i==4?menu_heap:0;}
#include "../tools/native/vehicle_slots.c"
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
static u32 config_body,config_tire,type_body,custom_texture,icon_calls;
static u32 effect_body,effect_tire;
static const char *last_body_prefix,*last_tire_prefix;
static const char *icon_name;
static u32 menu_texture(u32 resource,const struct NativeString *path){CHECK(resource==0x4321&&path->vtable==0x100d25d0);icon_name=path->text;icon_calls++;return custom_texture;}
static u32 next=0x80000,freed,last_icon,recipe_body,recipe_tire,prefix_body,prefix_tire,prefix_native;
static u32 heap(u32 g){CHECK(g==0x555);return 0x1000;}
static u32 alloc(u32 h,u32 n,u32 a){CHECK(h==0x1000&&a==4);u32 p=next;next=(next+n+15)&~15u;CHECK(next<sizeof(mem));return p;}
static void release(u32 h,u32 p){CHECK(h==0x1000&&p);freed++;}
static void append(u32 c,u32 id,u32 flag,u32 lock){u32 n=W(c,0x6a8),p=W(c,0x64)+n*16;CHECK(n<W(c,0x60));W(p,0)=id;W(p,12)=flag;B(p,8)=lock;W(c,0x6a8)=n+1;}
void original_vehicle_setup(u32 c,const u32 *kind,u32 single){(void)single;W(c,0x5c)=1;W(c,0x60)=*kind==0?40:*kind==1?22:15;W(c,0x64)=0x2000;}
void original_vehicle_body(u32 c,u32 unlock){(void)unlock;W(c,0x6a8)=0;for(u32 i=0;i<39;i++)append(c,i,0,0);append(c,0xffffffff,0,1);W(c,0x6c)=40;}
void original_vehicle_tire(u32 c,u32 unlock){(void)unlock;W(c,0x6a8)=0;for(u32 i=0;i<21;i++)append(c,i,0,0);append(c,0xffffffff,0,1);W(c,0x6c)=22;}
void original_vehicle_names(u32 c){u32 off[]={0x44,0x5c,0x4c,0x64};for(u32 j=0;j<4;j++){u32 n=j<2?40:22,p=0x10000+j*0x200;W(c,off[j])=n;W(c,off[j]+4)=p;for(u32 i=0;i<n;i++)W(p,i*4)=0x123000+j*100+i;}}
u32 original_vehicle_icon(u32 o,u32 k,u32 id,u32 d,u32 v){(void)o;(void)k;(void)d;(void)v;last_icon=id;return 0xfeed;}
void original_vehicle_prefix(u32 o,const char *p,u32 s){(void)o;(void)s;if(strstr(p,"/kart/body/"))last_body_prefix=p;if(strstr(p,"/kart/tire/"))last_tire_prefix=p;if(!strcmp(p,"custom/vehicles/Speeder8/Blue/kart/body/"))prefix_body++;else if(!strcmp(p,"custom/vehicles/SilverMonster/kart/tire/"))prefix_tire++;else prefix_native++;}
void original_vehicle_recipe(u32 o,u32 params,const u32 *r){(void)params;recipe_body=r[3];recipe_tire=r[6];costume_vehicle_prefix(o,"kart/body/",0);costume_vehicle_prefix(o,"kart/tire/",0);costume_vehicle_prefix(o,"custom/costumes/DK/Snorlax/driver/",0);}
u32 original_vehicle_type(u32 o,const u32 *body){type_body=*body;return o;}
u32 original_vehicle_config(u32 o,u32 p,const u32 *r){(void)p;config_body=r[0];config_tire=r[1];return o;}
u32 original_vehicle_effects(u32 o,u32 unit,u32 model,const u32 *p){CHECK(unit==123&&model==456);if(p){effect_body=p[0];effect_tire=p[1];}return o;}
u32 original_vehicle_body_name(u32 o,const u32 *b){(void)o;return *b;}
static void *resolve(u32 a){switch(a){case 0x0253d47c:return menu_texture;case 0x0273d360:return heap;case 0xaaaa:return alloc;case 0xbbbb:return release;case 0x025a4ed8:return append;default:fprintf(stderr,"Unknown service %x\n",a);exit(1);}}
int main(void){W(0x1018c7ec,0)=0x555;W(0x1000,12)=0x1100;W(0x1100,0x34)=0xaaaa;W(0x1100,0x3c)=0xbbbb;u32 c=0x30000,k=0;
 costume_vehicle_setup(c,&k,1);CHECK(W(c,0x60)==43);costume_vehicle_body(c,0);CHECK(W(c,0x6c)==43);CHECK(W(W(c,0x64)+40*16,0)==39);CHECK(B(W(c,0x64)+39*16,8)==1);CHECK(W(W(c,0x64)+41*16,0)==40&&W(W(c,0x64)+42*16,0)==41);
 k=1;costume_vehicle_setup(c,&k,1);costume_vehicle_tire(c,0);CHECK(W(c,0x60)==24&&W(c,0x6c)==24);CHECK(W(W(c,0x64)+22*16,0)==21&&W(W(c,0x64)+23*16,0)==22);
 k=2;u32 f=freed;costume_vehicle_setup(c,&k,1);CHECK(W(c,0x60)==15&&freed==f);
 costume_vehicle_names(c);CHECK(W(c,0x44)==43&&W(c,0x4c)==24);CHECK(W(W(c,0x48),40*4)==0x123008);CHECK(W(W(c,0x50),22*4)==0x123000+200+13);
 CHECK(costume_vehicle_icon(c,0,39,0,0)==0xfeed&&last_icon==7);costume_vehicle_icon(c,1,21,0,0);CHECK(last_icon==12);costume_vehicle_icon(c,0,7,0,0);CHECK(last_icon==7);
 menu_heap=0x9000;W(menu_heap,4)=0x4321;custom_texture=0xbeef;
 CHECK(costume_vehicle_icon(c,0,39,0,0)==0xbeef&&!strcmp(icon_name,"ct_KP_Speeder8^q.bflim"));
 CHECK(costume_vehicle_icon(c,1,21,0,0)==0xbeef&&!strcmp(icon_name,"ct_KP_SilverMonster^q.bflim"));
 CHECK(icon_calls==2);costume_vehicle_icon(c,0,7,0,0);costume_vehicle_icon(c,2,21,0,0);CHECK(icon_calls==2&&last_icon==21);
 custom_texture=0;CHECK(costume_vehicle_icon(c,1,21,0,0)==0xfeed&&last_icon==12);menu_heap=0;
 u32 r[9]={0,1,0,39,11,12,21,0,0};costume_vehicle_recipe(c,1,r);CHECK(r[3]==39&&r[6]==21);CHECK(recipe_body==7&&recipe_tire==12);CHECK(prefix_body==1&&prefix_tire==1&&prefix_native==1);CHECK(vehicle_body_scope==0&&vehicle_tire_scope==0);
 r[3]=7;r[6]=12;costume_vehicle_recipe(c,1,r);CHECK(prefix_body==1&&prefix_tire==1&&prefix_native==4);
 u32 source[7]={39,21,11,0,0,0,0};CHECK(vehicle_config_impl(0x60000,1,source)==0x60000);CHECK(source[0]==39&&source[1]==21);CHECK(config_body==7&&config_tire==12&&vehicle_flags(0x60000)==3);
 vehicle_remember((u32)(unsigned long long)r,3);costume_vehicle_recipe(c,1,r);CHECK(prefix_body==2&&prefix_tire==2);
 source[0]=7;source[1]=12;vehicle_config_impl(0x60000,1,source);CHECK(vehicle_flags(0x60000)==0);
 u32 extra=39,native=23;CHECK(costume_vehicle_type(c,&extra)==c&&type_body==7&&extra==39);costume_vehicle_type(c,&native);CHECK(type_body==23);
 u32 fx[2]={39,21};CHECK(costume_vehicle_effects(c,123,456,fx)==c&&effect_body==7&&effect_tire==12&&fx[0]==39&&fx[1]==21);
 fx[0]=23;fx[1]=4;costume_vehicle_effects(c,123,456,fx);CHECK(effect_body==23&&effect_tire==4);
 CHECK(costume_vehicle_body_name(c,&extra)==7&&extra==39);CHECK(costume_vehicle_body_name(c,&native)==23);
 CHECK(W(W(c,0x60),40*4)==0x7000 && W(W(c,0x68),22*4)==0x7001);
 for(u32 bi=0;bi<VEHICLE_BODY_COUNT;bi++)for(u32 ti=0;ti<VEHICLE_TIRE_COUNT;ti++) {
  source[0]=vehicle_body_choices[bi].id;source[1]=vehicle_tire_choices[ti].id;vehicle_config_impl(0x60000,1,source);
  CHECK(config_body==vehicle_body_choices[bi].donor&&config_tire==vehicle_tire_choices[ti].donor);
  CHECK(vehicle_flags(0x60000)==(vehicle_body_choices[bi].flag|vehicle_tire_choices[ti].flag));
  r[3]=config_body;r[6]=config_tire;
  vehicle_remember((u32)(unsigned long long)r,vehicle_flags(0x60000));costume_vehicle_recipe(c,1,r);
  CHECK(!strcmp(last_body_prefix,vehicle_body_choices[bi].prefix)&&!strcmp(last_tire_prefix,vehicle_tire_choices[ti].prefix));
  fx[0]=source[0];fx[1]=source[1];costume_vehicle_effects(c,123,456,fx);
  CHECK(effect_body==config_body&&effect_tire==config_tire&&fx[0]==source[0]&&fx[1]==source[1]);
  CHECK(W(W(c,0x60),(40+bi)*4)==vehicle_body_choices[bi].message);
  CHECK(W(W(c,0x68),(22+ti)*4)==vehicle_tire_choices[ti].message);
 }
 puts("PASS: canonical resource identities, reused recipe clears tags, added message IDs, new body class aliases donor");
 puts("PASS: expanded body/tire capacities, original entries and locked item preserved, glider untouched, name aliases, donor icons, custom recipe paths, original paths, costume paths, scope reset");return 0;}
