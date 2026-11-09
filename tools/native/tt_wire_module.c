/* Typed EUR81 NEX boundaries. No generic task or dispatcher hooks. */
typedef unsigned int u32;typedef unsigned char u8;
#ifndef W
#define W(p,o) (*(volatile u32 *)((u8 *)(__UINTPTR_TYPE__)(p)+(o)))
#define B(p,o) (*(volatile u8 *)((u8 *)(__UINTPTR_TYPE__)(p)+(o)))
#define FN(a,t) ((t)(__UINTPTR_TYPE__)(a))
#endif
extern volatile u32 pink_enabled;
#ifndef TT_WIRE_HOST
#include "tt_selection.h"
#endif
#ifdef ENABLE_TT_GHOST_SCOPE
struct String{const char *text;u32 vtable;};
extern u32 tt_options_import(u32);
static u32 settings_import(u32 address){return tt_options_import(address);}
#include "tt_ghost_scope.h"
#include "tt_online_ui.h"
#endif
#include "tt_wire.h"
#include "country_profile.h"
extern u32 tt_options_country(void);
extern void original_tt_country_profile(u32,u32,u32);
volatile u32 tt_country_profiles;
volatile u32 tt_country_profile_calls,tt_country_profile_caller,tt_country_profile_own;
void tt_country_profile(u32 source,u32 output,u32 own_mii){
 u32 caller=(u32)(__UINTPTR_TYPE__)__builtin_return_address(0);
 tt_country_profile_calls++;tt_country_profile_caller=caller;tt_country_profile_own=own_mii;
 original_tt_country_profile(source,output,own_mii);
 /* Both callers are in the LOCAL network profile builder 024063A4.
  * own_mii chooses the Mii source, not whether this is a local player.
  * The ordinary online branch passes zero; filtering on it lost the flag. */
 tt_country_profiles+=ctgp_profile_local_network((u8 *)(__UINTPTR_TYPE__)output,tt_options_country(),caller);
}
extern void original_tt_country_row(u32,u32,u32,u32,u32);
volatile u32 tt_country_rows,tt_country_row_old,tt_country_row_new;
void tt_country_row(u32 row,u32 time,u32 pid,u32 country,u32 wheel){
 u32 system=FN(0x024ce59cu,u32(*)(void))(),account=system?W(system,0x2d0):0;
 u32 profile=account?W(account,0x614):0,self=profile?W(profile,0x10):0;
 u32 chosen=ctgp_profile_row_country(tt_options_country(),self,pid,country);
 if(chosen!=country){tt_country_rows++;tt_country_row_old=country;tt_country_row_new=chosen;}
 original_tt_country_row(row,time,pid,chosen,wheel);
}
volatile u32 tt_wire_uploads,tt_wire_queries,tt_wire_targets,tt_wire_missing;
volatile u32 tt_wire_scores;
volatile u32 tt_wire_last_native,tt_wire_last_category,tt_wire_last_slot;
const char tt_wire_marker[]="MK8_TT_TYPED_WIRE_V1";
static u32 wire_category(u32 category){
 if(!tt_selected_valid||!W(0x1030c010u,0)||category!=tt_selected_native_course)return category;
 u32 mapped=ctgp_tt_wire_category(&tt_selected_category,category);
 if(!mapped){tt_wire_missing++;return 0xffffffffu;}
 tt_wire_last_native=category;tt_wire_last_category=mapped;tt_wire_last_slot=mapped-16;
 return mapped;
}
extern void original_tt_wire_upload(u32,u32,const u32*,u32,u32,u32);
void tt_wire_upload(u32 manager,u32 owner,const u32 *course,u32 name,u32 time,u32 flag){
 if(!course){original_tt_wire_upload(manager,owner,course,name,time,flag);return;}
 u32 mapped=wire_category(*course);
 if(mapped==0xffffffffu)return; /* Unknown revision must not overwrite donor board. */
 if(mapped!=*course)tt_wire_uploads++;
 original_tt_wire_upload(manager,owner,&mapped,name,time,flag);
}
extern void original_tt_wire_score(u32,const u32*,u32,u32,u32,u32,u32);
void tt_wire_score(u32 manager,const u32 *course,u32 time,u32 unused,u32 high,u32 low,u32 flag){
 if(!course){original_tt_wire_score(manager,course,time,unused,high,low,flag);return;}
 u32 mapped=wire_category(*course);
 if(mapped==0xffffffffu)return;
 if(mapped!=*course)tt_wire_scores++;
 original_tt_wire_score(manager,&mapped,time,unused,high,low,flag);
}
extern void original_tt_wire_query(u32,const u32*,u32);
void tt_wire_query(u32 manager,const u32 *course,u32 scope){
 if(!course){original_tt_wire_query(manager,course,scope);return;}
 u32 mapped=wire_category(*course);
 if(mapped==0xffffffffu)return;
 if(mapped!=*course)tt_wire_queries++;
 original_tt_wire_query(manager,&mapped,scope);
}
extern u32 original_tt_wire_target(const u32*);
u32 tt_wire_target(const u32 *course){
 if(!course)return original_tt_wire_target(course);
 u32 mapped=wire_category(*course);
 if(mapped==0xffffffffu)return 0xffff;
 if(mapped!=*course)tt_wire_targets++;
 return original_tt_wire_target(&mapped);
}
