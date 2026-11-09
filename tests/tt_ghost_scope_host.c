#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
/* Pointer-sized tokens let the host exercise routing without dereferencing game addresses. */
typedef uintptr_t u32;typedef unsigned char u8;
struct String{const char *text;u32 vtable;};
static struct{u32 key,value;} words[4096];static unsigned word_count;
static u32 *word(u32 key){for(unsigned i=0;i<word_count;i++)if(words[i].key==key)return &words[i].value;assert(word_count<4096);words[word_count].key=key;return &words[word_count++].value;}
static u8 manager_bytes[0x55304],profile_bytes[256];
static u8 native_personal[0x6900];
static u8 *byte(u32 address){if(address>=0x100000&&address<0x155304)return manager_bytes+address-0x100000;if(address>=0x3000&&address<0x3100)return profile_bytes+address-0x3000;return (u8*)address;}
#define W(p,o) (*word((p)+(o)))
#define B(p,o) (*byte((p)+(o)))
static void *host_function(u32 address);
#define FN(address,type) ((type)host_function(address))
#include "../tools/native/tt_category.h"
static u32 tt_selected_valid=1,tt_selected_count=1;
static const struct CtgpTTTrack track={"Gu_Test","ct.test","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"};
static struct CtgpTTCategory tt_selected_category={&track,200,0};
static char tt_selected_identity[96]="ct.test",tt_selected_path[256];
static unsigned loads,mkdirs,original_gets,entered,removes,dialog_closes;
static char observed_directory[256],observed_remove[256];
static const char *format_used;
#define TT_GHOST_SCOPE_HOST
#include "../tools/native/tt_ghost_scope.h"

static void clear_rows(void *rows,unsigned count){memset(rows,0,count*0x1a4);for(unsigned i=0;i<count;i++){u32 row=(u32)rows+i*0x1a4;for(unsigned j=0;j<4;j++)W(row,j*4)=0xffffffffu;W(row,0x14)=4;W(row,0x98)=row+0xa4;}}
static void init_personal(void *rows){clear_rows(rows,64);}
static void init_staff(void *rows){clear_rows(rows,48);}
static void load_rows(u32 owner,u32 device,u32 rows,u32 count,u32 first,const char *path,const char *prefix,u32 cleanup){
 (void)owner;(void)device;(void)first;assert(!cleanup);assert(strstr(path,"/custom/tt"));loads++;
 if(count!=48)return;
 for(unsigned i=0;i<4;i++){W(rows,i*4)=1;}
 W(rows,0x14)=0;W(rows,0x98)=rows+0xa4;
 snprintf((char*)(rows+0xa4),256,"%sRecorded.dat",prefix);
}
static u32 copy_record(u32 destination,u32 source){
 (void)source;W(destination,0x98)=destination+0xa4;W(destination,0x9c)=0x100ddb3c;W(destination,0xa0)=256;
 B(destination,0xa4)=0;return destination;
}
static u32 system_get(void){return 0x1000;}
static u32 device_get(u32 slot){assert(slot==1);return 0x1800;}
static int add_client(void *client,u32 flags){(void)client;(void)flags;return 0;}
static void init_command(void *command){(void)command;}
static int del_client(void *client,u32 flags){(void)client;(void)flags;return 0;}
static int acquire(const char *name,u32 *module){assert(!strcmp(name,"nn_save.rpl"));*module=7;return 0;}
static int find_export(u32 module,u32 data,const char *name,u32 *address){assert(module==7&&!data&&!strcmp(name,"SAVEMakeDir"));*address=0xdead;return 0;}
static int make_dir(void *client,void *command,u32 slot,const char *path,u32 flags){(void)client;(void)command;(void)flags;assert(slot==1&&strstr(path,"/custom")==path);mkdirs++;return 0;}
static u32 format(u32 target,const char *fmt,...){(void)target;format_used=fmt;return 42;}
static void close_dialog(u32 page,u32 dialog){(void)page;(void)dialog;dialog_closes++;}
static void *host_function(u32 address){switch(address){
 case 0x24f0994:return (void*)init_personal;case 0x24f08f4:return (void*)init_staff;case 0x24eecf8:return (void*)load_rows;
 case 0x25caca0:return (void*)copy_record;
 case 0x24ce59c:return (void*)system_get;case 0x24ce1ac:return (void*)device_get;
 case 0x23b143c:return (void*)add_client;case 0x23b1444:return (void*)init_command;case 0x2714af8:return (void*)del_client;
 case 0x249eac8:return (void*)acquire;case 0x26789dc:return (void*)find_export;case 0xdead:return (void*)make_dir;
 case 0x253fe60:return (void*)close_dialog;
 case 0x2740e1c:return (void*)format;default:assert(0);return 0;
}}
static u32 settings_import(u32 address){return address;}
u32 original_tt_personal_get(u32 manager,u32 slot){(void)manager;original_gets++;if(slot==0xff&&!tt_scope_ready)return (u32)native_personal;return 0x9000+slot;}
void original_tt_list_build(u32 page){(void)page;entered++;assert(!memcmp(manager_bytes+0x50444,tt_staff_view,sizeof tt_staff_view));for(unsigned i=0;i<48;i++){u32 row=(u32)tt_staff_view+i*0x1a4;assert(W(row,0x9c)==0x100ddb3c&&W(row,0x98)==row+0xa4);}assert(tt_personal_get(1,0xff)==(u32)tt_personal_view);}
void original_tt_ghost_enter(u32 page){tt_list_build(page);}
static unsigned forwarded_events;
void original_tt_ghost_event(u32 page,u32 event){(void)page;(void)event;forwarded_events++;}
void original_tt_name_generate(u32 properties,u32 output){(void)properties;strcpy((char*)W(output,0),"gsNew.dat");}
void original_tt_directory(u32 iterator,const struct String *directory,const struct String *prefix,const struct String *suffix){(void)iterator;(void)prefix;(void)suffix;snprintf(observed_directory,sizeof observed_directory,"%s",directory->text);}
void original_tt_personal_reload(u32 records,u32 slot,u32 cleanup){(void)slot;assert(!cleanup);clear_rows((void*)records,64);load_rows(records,1,records,48,16,tt_scope_personal_path,"gs",0);}
void original_tt_remove(u32 manager,const struct String *name){(void)manager;removes++;snprintf(observed_remove,sizeof observed_remove,"%s",name->text);}
void original_tt_save_record(u32 manager,u32 properties,u32 mode){(void)properties;(void)mode;W(manager,0xcc)=0x7000;W(0x7000,0x148)=93832;}
u32 original_tt_mgr_start(u32 manager,u32 task,u32 param,u32 size){(void)manager;(void)task;assert(size==8&&W(param,0)==0&&W(param,4)==0x12345678);return 77;}
void original_tt_upload_sequence(u32 page,u32 dialog){(void)page;(void)dialog;dialog_closes++;}
int main(void){
 W(0x1000,0x2c8)=0x100000;W(0x1000,0x2d0)=0x2000;W(0x2000,0x614)=0x3000;profile_bytes[0x78]=1;W(0x1030c010,0)=1;
 memset(manager_bytes+0x50444,0xa5,0x4ec0);assert(ctgp_tt_path(&tt_selected_category,tt_selected_path,sizeof tt_selected_path));
 tt_ghost_enter(46);assert(entered==1&&loads==3&&tt_scope_dirs_ready&&mkdirs==7);
 for(unsigned i=0;i<0x4ec0;i++)assert(manager_bytes[0x50444+i]==0xa5);
 assert(strstr((char*)tt_personal_view+0xa4,tt_scope_personal_path)==(char*)tt_personal_view+0xa4);
 assert(tt_personal_get(1,2)==0x9002&&original_gets==2);assert(tt_scope_personal_reads==1);
 struct String root={"/",1},gs={"gs",1},dat={".dat",1};tt_directory(1,&root,&gs,&dat);assert(!strcmp(observed_directory,tt_scope_personal_path));
 char name[256];W(0x4000,0)=(u32)name;W(0x4000,8)=sizeof name;tt_name_generate(1,0x4000);assert(strstr(name,tt_scope_personal_path)==name);
 struct String remove_name={"gsOld.dat",1};tt_remove(1,&remove_name);assert(removes==1&&strstr(observed_remove,tt_scope_personal_path)==observed_remove);
 tt_personal_reload((u32)tt_personal_view,1,1);assert(strstr((char*)tt_personal_view+0xa4,tt_scope_personal_path)==(char*)tt_personal_view+0xa4);
 tt_staff_format(1,"ghost/%s/%s","slow","/custom/tt_staff/test/sgRecorded.dat");assert(!strcmp(format_used,"%s"));
 u8 page[0x500]={0};u32 event=0x5000;B((u32)page,0x37c)=1;W(event,8)=1;W(event,0x14)=2;W(event,0xc)=0x6a;
 tt_ghost_event((u32)page,event);assert(!forwarded_events&&tt_empty_actions_blocked==1);
 W(event,0xc)=0x6c;tt_ghost_event((u32)page,event);assert(tt_online_requests==1&&forwarded_events==1);
 W(event,0xc)=0x6c;tt_ghost_event((u32)page,event);assert(tt_online_requests==2&&forwarded_events==2);
 W(event,0xc)=0x68;tt_ghost_event((u32)page,event);assert(forwarded_events==3);
 tt_scope_ready=0;assert(tt_personal_get(1,0xff)==(u32)tt_personal_view&&tt_scope_ready&&tt_scope_loads==2);
 tt_upload_sequence((u32)page,1);assert(dialog_closes==1&&tt_native_uploads_blocked==0);
 tt_save_record(0x6000,0,0);assert(W(0x7000,0x148)==93832&&tt_net_job_patches==0);
 u32 task=0x8000,param=0x8100;W(task,0)=7;W(param,0)=0;W(param,4)=0x12345678;assert(tt_mgr_start(0x6000,task,param,8)==77&&W(param,0)==0&&W(param,4)==0x12345678&&tt_net_remaps==0);
 W(0x1030c010,0)=0;tt_directory(1,&root,&gs,&dat);assert(!strcmp(observed_directory,"/"));assert(tt_personal_get(1,0xff)==0x90ff);
 tt_remove(1,&remove_name);assert(!strcmp(observed_remove,"gsOld.dat"));
 /* Switching the same CT between classes must reload a different directory,
  * including when returning to an already visited category. */
 W(0x1030c010,0)=1;
 for(unsigned pass=0;pass<3;pass++){
  tt_selected_category.cc=pass==1?200:150;tt_selected_count++;
  assert(ctgp_tt_path(&tt_selected_category,tt_selected_path,sizeof tt_selected_path));
  tt_scope_prepare();
  assert(strstr(tt_scope_personal_path,pass==1?"/200/n1/":"/150/n1/"));
  assert(strstr((char*)tt_personal_view+0xa4,tt_scope_personal_path)==(char*)tt_personal_view+0xa4);
 }
 strcpy(tt_selected_identity,"native.gu_firstcircuit");tt_selected_category.cc=150;tt_selected_category.pink=0;W(0x1030c010,0)=1;
 assert(!tt_category_active());assert(tt_personal_get(1,0xff)==0x90ff);
 puts("Ghost cache routing, official staff restoration, account isolation, private writes/deletes and native fallback passed");
}
