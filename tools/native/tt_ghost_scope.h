/* Selected-category ghost views and private account paths. */
extern void original_tt_ghost_enter(u32);
extern u32 original_tt_personal_get(u32,u32);
extern void original_tt_name_generate(u32,u32);
extern void original_tt_directory(u32,const struct String*,const struct String*,const struct String*);
extern void original_tt_personal_reload(u32,u32,u32);
extern void original_tt_remove(u32,const struct String*);
#ifndef TT_GHOST_ADDRESS
#define TT_GHOST_ADDRESS(pointer) ((u32)(__UINTPTR_TYPE__)(pointer))
#endif
static u8 tt_personal_view[0x6900] __attribute__((aligned(64)));
static u8 tt_staff_view[0x4ec0] __attribute__((aligned(64)));
static u8 tt_staff_original[0x4ec0] __attribute__((aligned(64)));
static u32 tt_scope_ready,tt_scope_generation,tt_scope_slot,tt_scope_staff;
volatile u32 tt_scope_loads,tt_scope_personal_reads,tt_scope_staff_swaps,tt_scope_path_errors;
char tt_scope_personal_path[256],tt_scope_staff_path[256];
#include "tt_ghost_dirs.h"
static int tt_starts(const char *value,const char *prefix){if(!value)return 0;while(*prefix)if(*value++!=*prefix++)return 0;return 1;}
static u32 tt_category_active(void){return tt_selected_valid&&W(0x1030c010u,0)&&
 (tt_starts(tt_selected_identity,"ct.")||tt_selected_category.cc==200||tt_selected_category.pink);}
static u32 tt_ghost_active(void){return tt_scope_ready&&tt_category_active()&&tt_scope_generation==tt_selected_count;}
static int tt_record_present(u32 row){return W(row,0)!=0xffffffffu&&W(row,4)!=0xffffffffu&&W(row,8)!=0xffffffffu&&W(row,12)!=0xffffffffu&&W(row,0x14)!=4;}
static void tt_prefix_records(u32 rows,u32 count,const char *prefix){
 for(u32 i=0;i<count;i++){
  u32 row=rows+i*0x1a4;if(!tt_record_present(row))continue;
  const char *name=(const char *)(__UINTPTR_TYPE__)W(row,0x98);
  if(tt_starts(name,prefix))continue;
  char path[256];unsigned used=0;path[0]=0;
  if(!name||!(tt_starts(name,"gs")||tt_starts(name,"dg")||tt_starts(name,"sg"))||
      !ctgp_tt_append(path,sizeof path,&used,prefix)||!ctgp_tt_append(path,sizeof path,&used,name)){
   W(row,0)=0xffffffffu;tt_scope_path_errors++;continue;
  }
  for(u32 j=0;j<=used;j++)B(row,0xa4+j)=(u8)path[j];
  W(row,0x98)=row+0xa4; /* Native owned filename buffer (256 bytes). */
 }
}
static void tt_scope_prepare(void){
 if(!tt_selected_valid){tt_scope_ready=0;return;}
 if(tt_ghost_active())return;
 tt_scope_ready=0;tt_scope_generation=tt_selected_count;tt_scope_slot=0;tt_scope_dirs_ready=0;
 /* Clear routines reset race metadata only; they do not construct SafeString.
  * The native list copy-constructs even empty records, so every row needs a
  * live filename vtable and an owned inline buffer before it can be exposed. */
 u32 system=FN(0x024ce59cu,u32(*)(void))(),manager=system?W(system,0x2c8):0;
 if(!manager){tt_scope_path_errors++;return;}
 u32 source=original_tt_personal_get(manager,0xff);
 if(!source){tt_scope_path_errors++;return;}
 typedef u32(*CopyRecord)(u32,u32);
 for(u32 i=0;i<64;i++){
  u32 row=TT_GHOST_ADDRESS(tt_personal_view)+i*0x1a4;
  FN(0x025caca0u,CopyRecord)(row,source+i*0x1a4);B(row,0xa4)=0;
 }
 for(u32 i=0;i<48;i++){
  u32 row=TT_GHOST_ADDRESS(tt_staff_view)+i*0x1a4;
  FN(0x025caca0u,CopyRecord)(row,manager+0x50444+i*0x1a4);B(row,0xa4)=0;
 }
 FN(0x024f0994u,void(*)(void*))(tt_personal_view);
 FN(0x024f08f4u,void(*)(void*))(tt_staff_view);
 unsigned used=0;tt_scope_personal_path[0]=0;
 if(!ctgp_tt_append(tt_scope_personal_path,256,&used,"/")||!ctgp_tt_append(tt_scope_personal_path,256,&used,tt_selected_path)){tt_scope_path_errors++;return;}
 used=0;tt_scope_staff_path[0]=0;
 if(!ctgp_tt_append(tt_scope_staff_path,256,&used,"/custom/tt_staff/")||!ctgp_tt_append(tt_scope_staff_path,256,&used,tt_selected_path+13)){tt_scope_path_errors++;return;}
 typedef void(*Load)(u32,u32,u32,u32,u32,const char*,const char*,u32);
 u32 personal=TT_GHOST_ADDRESS(tt_personal_view),staff=TT_GHOST_ADDRESS(tt_staff_view);
 u32 account=W(system,0x2d0),profile=account?W(account,0x614):0;
 tt_scope_slot=profile?B(profile,0x78):0;
 tt_ensure_dirs();
 if(tt_scope_slot>=1&&tt_scope_slot<=12){
  u32 device=FN(0x024ce1acu,u32(*)(u32))(tt_scope_slot);
  if(device){
   FN(0x024eecf8u,Load)(personal,device,personal,48,16,tt_scope_personal_path,"gs",0);
   FN(0x024eecf8u,Load)(personal,device,personal+0x4ec0,16,0,tt_scope_personal_path,"dg",0);
  }
 }
 tt_scope_staff=tt_starts(tt_selected_identity,"ct.")||tt_selected_category.cc==200||tt_selected_category.pink;
 if(tt_scope_staff){FN(0x024eecf8u,Load)(staff,0,staff,48,16,tt_scope_staff_path,"sg",0);tt_prefix_records(staff,48,tt_scope_staff_path);}
 tt_prefix_records(personal,64,tt_scope_personal_path);
 tt_scope_ready=1;tt_scope_loads++;
}
u32 tt_personal_get(u32 manager,u32 slot){
 if(tt_category_active()&&!tt_ghost_active())tt_scope_prepare();
 if(tt_ghost_active()&&(slot==0xff||slot==tt_scope_slot)){tt_scope_personal_reads++;return TT_GHOST_ADDRESS(tt_personal_view);}
 return original_tt_personal_get(manager,slot);
}
extern void original_tt_list_build(u32);
extern void original_tt_ghost_event(u32,u32);
volatile u32 tt_online_requests,tt_empty_actions_blocked;
static u32 tt_scope_reload_pending;
void tt_list_build(u32 page){
 u32 system=FN(0x024ce59cu,u32(*)(void))(),manager=system?W(system,0x2c8):0;
 u32 swap=manager&&tt_ghost_active()&&tt_scope_staff;
 if(swap){for(u32 i=0;i<sizeof tt_staff_view;i++){tt_staff_original[i]=B(manager,0x50444+i);B(manager,0x50444+i)=tt_staff_view[i];}tt_scope_staff_swaps++;}
 original_tt_list_build(page);
 if(swap)for(u32 i=0;i<sizeof tt_staff_view;i++)B(manager,0x50444+i)=tt_staff_original[i];
}
void tt_ghost_enter(u32 page){if(tt_scope_reload_pending){tt_scope_ready=0;tt_scope_reload_pending=0;}tt_scope_prepare();original_tt_ghost_enter(page);}
void tt_ghost_event(u32 page,u32 event){
 if(tt_category_active()&&!tt_ghost_active())tt_scope_prepare();
 if(tt_ghost_active()&&page&&event&&B(page,0x37c)&&W(event,8)&&W(event,0x14)==2){
  u32 action=W(event,0xc),list=W(page,0x36c);
  /* Never submit a custom/200/pink recording to the donor's Nintendo board. */
  if(action==0x6c){tt_online_requests++;original_tt_ghost_event(page,event);return;}
  if(action==0x6b){tt_online_requests++;original_tt_ghost_event(page,event);return;}
  if((action==0x69||action==0x6a)&&(!list||!W(list,0xd8))){tt_empty_actions_blocked++;return;}
 }
 original_tt_ghost_event(page,event);
}
u32 tt_staff_format(u32 target,const char *format,const char *first,const char *second){
 typedef u32(*Format)(u32,const char*,...);
 if(tt_ghost_active()&&tt_starts(second,"/custom/tt_staff/"))return FN(0x02740e1cu,Format)(target,"%s",second);
 return FN(0x02740e1cu,Format)(target,format,first,second);
}
/* Route the root-directory enumeration used by native reload/orphan cleanup.
 * Other save files and non-ghost directory iterators remain native. */
void tt_directory(u32 iterator,const struct String *directory,const struct String *prefix,const struct String *suffix){
 struct String scoped;
 if(tt_ghost_active()&&directory&&prefix&&ctgp_tt_equal(directory->text,"/")&&
    (ctgp_tt_equal(prefix->text,"gs")||ctgp_tt_equal(prefix->text,"dg"))){
  scoped=*directory;scoped.text=tt_scope_personal_path;
  original_tt_directory(iterator,&scoped,prefix,suffix);return;
 }
 original_tt_directory(iterator,directory,prefix,suffix);
}
static int tt_scope_name(char *output,u32 capacity,const char *name){
 if(!name||!(tt_starts(name,"gs")||tt_starts(name,"dg")))return 0;
 unsigned used=0;output[0]=0;
 if(!ctgp_tt_append(output,capacity,&used,tt_scope_personal_path)||!ctgp_tt_append(output,capacity,&used,name))return -1;
 return 1;
}
volatile u32 tt_save_name_calls,tt_save_name_scoped,tt_save_record_calls,tt_save_record_finished;
void tt_name_generate(u32 properties,u32 output){
 tt_save_name_calls++;
 if(tt_category_active()&&!tt_ghost_active())tt_scope_prepare();
 original_tt_name_generate(properties,output);
 if(!tt_ghost_active()||!output||!W(output,0))return;
 tt_ensure_dirs();
 char path[256];char *name=(char *)(__UINTPTR_TYPE__)W(output,0);
 u32 capacity=W(output,8);if(capacity>sizeof path)capacity=sizeof path;
 int scoped=tt_scope_name(path,capacity,name);
 if(scoped){
  if(scoped<0){name[0]=0;tt_scope_path_errors++;return;}
  for(u32 i=0;;i++){name[i]=path[i];if(!path[i])break;}
  tt_save_name_scoped++;
 }
}
void tt_personal_reload(u32 records,u32 slot,u32 cleanup){
 original_tt_personal_reload(records,slot,tt_ghost_active()&&records==TT_GHOST_ADDRESS(tt_personal_view)?0:cleanup);
 if(tt_ghost_active()&&records==TT_GHOST_ADDRESS(tt_personal_view))tt_prefix_records(records,64,tt_scope_personal_path);
}
void tt_remove(u32 manager,const struct String *name){
 if(tt_ghost_active()&&name){
  char path[256];int scoped=tt_scope_name(path,sizeof path,name->text);
  if(scoped<0){tt_scope_path_errors++;return;}
  if(scoped){struct String redirected=*name;redirected.text=path;original_tt_remove(manager,&redirected);return;}
 }
 original_tt_remove(manager,name);
}

#ifndef TT_GHOST_SCOPE_HOST
extern void original_tt_footer(u32,u32);
void tt_footer(u32 control,u32 course){
 original_tt_footer(control,course);
 u32 owner=control?W(control,4):0;
 if(!tt_selected_valid||!tt_selected_page||!W(0x1030c010u,0)||!owner||W(owner,4)!=46)return;
 if(tt_selected_name_message)FN(0x02536848u,void(*)(u32,u32,u32))(control,W(control,0x60),tt_selected_name_message);
 u32 prefix=W(control,0x5c);
 FN(0x02531bdcu,void(*)(u32,u32,u32))(control,prefix,tt_selected_prefix_message!=0&&tt_selected_prefix_message!=0xffffffffu);
 if(tt_selected_prefix_message&&tt_selected_prefix_message!=0xffffffffu)FN(0x02536848u,void(*)(u32,u32,u32))(control,prefix,tt_selected_prefix_message);
 u32 picture=W(control,0x64),vt=picture?W(picture,8):0,method=vt?W(vt,0x4c):0;
 if(tt_selected_preview_ready&&method){
  u32 material=FN(method,u32(*)(u32,u32))(picture,0),maps=material?W(material,0x10):0;
  if(maps)for(u32 i=0;i<28;i++)B(maps,0x1c+i)=tt_selected_preview_map[i];
 }
}
#endif

extern void original_tt_save_record(u32,u32,u32);
volatile u32 tt_net_job_patches,tt_net_job_old;
void tt_save_record(u32 manager,u32 properties,u32 mode){
 tt_save_record_calls++;
 if(tt_category_active()&&!tt_ghost_active())tt_scope_prepare();
 original_tt_save_record(manager,properties,mode);
 /* job+0x148 is the replay payload size copied from ghostRecord+8,
  * NOT a course/category id. Never replace it with a persistence slot. */
 tt_save_record_finished++;
}
extern void original_tt_upload_sequence(u32,u32);
volatile u32 tt_native_uploads_blocked;
/* The generic job manager accepts heterogeneous parameter blocks. Their
 * first word can be a recorder/player index, a course id or another value.
 * Preserve them until remapping is implemented at the typed NEX boundary. */
extern u32 original_tt_mgr_start(u32,u32,u32,u32);
volatile u32 tt_net_remaps,tt_net_last_slot,tt_net_last_type;
u32 tt_mgr_start(u32 manager,u32 task,u32 param,u32 size){
 if(task)tt_net_last_type=W(task,0);
 return original_tt_mgr_start(manager,task,param,size);
}
void tt_upload_sequence(u32 page,u32 dialog){
 /* Native transport remains unchanged; typed CTGP remapping is pending. */
 original_tt_upload_sequence(page,dialog);
}
