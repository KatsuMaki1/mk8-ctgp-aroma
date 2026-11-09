/* Extend the existing Options country row without rebuilding other Options
 * code. Keep the same country-ID journal format and native settings I/O. */
typedef unsigned int u32;
typedef unsigned short u16;
#include "extra_countries_catalog.h"
struct LocalLanguage {
 const char *code; const u16 *name,*country,*automatic,*language,*speed,*on,*off;
 const u16 *const *countries; const void *messages; u32 count;
};
struct OptionModel {u32 unused,vtable,index,pad;unsigned char style;};
extern const struct LocalLanguage old_languages[];
extern volatile u32 old_country_choice,old_options,old_settings_loaded;
extern volatile u32 old_settings_dirty,old_settings_sequence,old_settings_reads;
extern volatile u32 old_settings_writes,old_settings_errors,old_language_choice;
extern volatile u32 old_pink_enabled;
extern u32 old_language_index(void),old_settings_language_id(u32);
extern void old_language_set(u32),old_option_text(u32,const u16*,const u16*,u32);
extern int old_settings_transfer(u32,u32*,u32);
extern const u16 *original_extra_model_value(struct OptionModel*);
extern void original_extra_model_change(struct OptionModel*,const u32*);
static u16 value_buffer[32];
#ifdef EXTRA_COUNTRIES_HOST
extern volatile u32 extra_test_speed;
#define EXTRA_SPEED extra_test_speed
#else
#define EXTRA_SPEED (*(volatile u32*)0x10305000u)
#endif
const char extra_countries_marker[]="CTGP_COUNTRIES_254_V1";
static u32 safe_choice(void){return old_country_choice<EXTRA_COUNTRY_COUNT?old_country_choice:0;}
static const u16 *country_name(void){
 u32 lang=old_language_index(),choice=safe_choice();if(lang>=8)lang=0;
 return choice<EXTRA_OLD_COUNT?old_languages[lang].countries[choice]:extra_labels[lang][choice-EXTRA_OLD_COUNT];
}
u32 extra_selected_country(void){return extra_country_ids[safe_choice()];}
void extra_country_label(u32 control){
 u32 lang=old_language_index();if(lang>=8)lang=0;
 old_option_text(control,old_languages[lang].country,country_name(),1);
}
const u16 *extra_model_value(struct OptionModel *model){
 if(model->index!=1)return original_extra_model_value(model);
 const u16 *s=country_name();u32 n=0;
 while(n<26&&s[n]){value_buffer[n]=s[n];n++;}
 if(s[n])value_buffer[n++]=0x2026;
 value_buffer[n]=0;return value_buffer;
}
void extra_model_change(struct OptionModel *model,const u32 *direction){
 if(model->index!=1){original_extra_model_change(model,direction);return;}
 if(!old_options)return;
 u32 choice=safe_choice();
 old_country_choice=*direction==2?(choice?choice-1:EXTRA_COUNTRY_COUNT-1):(choice+1)%EXTRA_COUNTRY_COUNT;
 old_settings_loaded=1;old_settings_dirty=45;
}
static u32 checksum(const u32 *v){u32 h=2166136261u;for(u32 i=0;i<7;i++)h=(h^v[i])*16777619u;return h;}
static int valid(const u32 *v){
 if(v[0]!=0x43544f50u||v[1]!=1||v[3]>1||v[4]>1||v[7]!=checksum(v))return 0;
 u32 country=0,language=v[6]==0;
 for(u32 i=0;i<EXTRA_COUNTRY_COUNT;i++)if(extra_country_ids[i]==v[5])country=1;
 for(u32 i=1;i<=8;i++)if(old_settings_language_id(i)==v[6])language=1;
 return country&&language;
}
void extra_settings_load(void){
 if(old_settings_loaded)return;
 u32 a[8],b[8],*best=0;
 if(old_settings_transfer(0,a,0)&&valid(a))best=a;
 if(old_settings_transfer(1,b,0)&&valid(b)&&(!best||(int)(b[2]-best[2])>0))best=b;
 if(!best)return;
 old_settings_loaded=1;old_settings_sequence=best[2];
 EXTRA_SPEED=best[3];old_pink_enabled=best[4];
 for(u32 i=0;i<EXTRA_COUNTRY_COUNT;i++)if(extra_country_ids[i]==best[5])old_country_choice=i;
 u32 language=0;for(u32 i=1;i<=8;i++)if(old_settings_language_id(i)==best[6])language=i;
 old_language_set(language);old_settings_reads++;
}
void extra_settings_save(void){
 if(!old_settings_dirty)return;
 u32 v[8]={0x43544f50u,1,old_settings_sequence+1,!!EXTRA_SPEED,!!old_pink_enabled,extra_selected_country(),old_settings_language_id(old_language_choice),0};
 v[7]=checksum(v);
 if(old_settings_transfer(v[2]&1,v,1)){old_settings_sequence=v[2];old_settings_dirty=0;old_settings_writes++;}
 else{old_settings_errors++;old_settings_dirty=120;}
}
