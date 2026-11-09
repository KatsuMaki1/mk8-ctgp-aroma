#include <assert.h>
#include <string.h>
#include <stdio.h>
#define EXTRA_COUNTRIES_HOST
#include "../tools/native/extra_countries.c"
volatile u32 old_country_choice,old_options,old_settings_loaded,old_settings_dirty;
volatile u32 old_settings_sequence,old_settings_reads,old_settings_writes,old_settings_errors;
volatile u32 old_language_choice,old_pink_enabled,extra_test_speed;
static const u16 original_name[]={65,0};
static const u16 *const original_names[122]={[0]=original_name,[1]=original_name};
const struct LocalLanguage old_languages[8]={{.countries=original_names},{.countries=original_names},
 {.countries=original_names},{.countries=original_names},{.countries=original_names},
 {.countries=original_names},{.countries=original_names},{.countries=original_names}};
static u32 locale,delegated_value,delegated_change,journal[2][8],available[2],fail_write;
u32 old_language_index(void){return locale;}
u32 old_settings_language_id(u32 i){return i?0x6560+i:0;}
void old_language_set(u32 i){old_language_choice=i;}
void old_option_text(u32 c,const u16 *l,const u16 *v,u32 i){(void)c;(void)l;(void)v;(void)i;}
int old_settings_transfer(u32 slot,u32 *v,u32 write){
 if(write){if(fail_write)return 0;memcpy(journal[slot],v,32);available[slot]=1;return 1;}
 if(!available[slot])return 0;
 memcpy(v,journal[slot],32);return 1;
}
const u16 *original_extra_model_value(struct OptionModel *m){(void)m;delegated_value++;return original_name;}
void original_extra_model_change(struct OptionModel *m,const u32 *d){(void)m;(void)d;delegated_change++;}
int main(void){
 assert(EXTRA_COUNTRY_COUNT==254&&EXTRA_OLD_COUNT==122);
 unsigned char seen[256]={0};
 for(u32 i=0;i<EXTRA_COUNTRY_COUNT;i++){assert(extra_country_ids[i]<255);assert(!seen[extra_country_ids[i]]++);}
 assert(!seen[222]);
 for(locale=0;locale<8;locale++)for(u32 i=122;i<254;i++){
  old_country_choice=i;assert(country_name()&&country_name()[0]);
  struct OptionModel m={.index=1};const u16 *v=extra_model_value(&m);u32 n=0;while(v[n])n++;assert(n<=27);
 }
 locale=0;old_options=1;struct OptionModel m={.index=1};u32 left=2,right=1;
 old_country_choice=0;extra_model_change(&m,&left);assert(old_country_choice==253);
 extra_model_change(&m,&right);assert(old_country_choice==0);
 old_country_choice=121;extra_model_change(&m,&right);assert(old_country_choice==122);
 u32 new_id=extra_selected_country();extra_test_speed=1;old_pink_enabled=1;old_language_choice=2;
 extra_settings_save();assert(old_settings_writes==1&&old_settings_dirty==0);
 old_settings_loaded=0;old_country_choice=0;old_pink_enabled=0;extra_test_speed=0;
 extra_settings_load();assert(old_country_choice==122&&extra_selected_country()==new_id);
 assert(old_pink_enabled==1&&extra_test_speed==1&&old_language_choice==2);
 /* A newer checksum-invalid slot must not discard the valid older settings. */
 memcpy(journal[0],journal[1],32);available[0]=1;journal[0][2]+=100;
 old_settings_loaded=0;extra_settings_load();assert(extra_selected_country()==new_id);
 old_settings_dirty=1;fail_write=1;extra_settings_save();assert(old_settings_dirty==120&&old_settings_errors==1);
 m.index=0;extra_model_value(&m);extra_model_change(&m,&right);assert(delegated_value==1&&delegated_change==1);
 puts("Expanded countries: names, wraparound, journal restart/corruption, and other-row delegation passed.");
 return 0;
}
