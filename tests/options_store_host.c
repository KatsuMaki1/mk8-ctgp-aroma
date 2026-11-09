#include <stdint.h>
#include <assert.h>
#include <string.h>
#include <stdio.h>
typedef uint32_t u32;typedef unsigned char u8;
static u32 speed=1,pink_enabled,country_choice,language_choice;
static const u32 country_ids[]={0,77,49};
static const struct {const char *code;} languages[]={{"ee"},{"ef"}};
#define COUNTRY_COUNT 3u
#define LANGUAGE_COUNT 2u
#define OPTIONS_STORE_TEST
#define W(p,o) speed
static void language_set(u32 c){language_choice=c;}
static void country_apply(void){}
#include "../tools/native/options_store.h"
static u32 disk[2][8],exists[2],fail_write;
int settings_transfer(u32 slot,u32 *words,u32 write){
 if(write){if(fail_write)return 0;memcpy(disk[slot],words,32);exists[slot]=1;return 1;}
 if(!exists[slot])return 0;memcpy(words,disk[slot],32);return 1;
}
int main(void){
 assert(settings_branch_target(0x23b143c,0x4aa4ec29)==0xe00064);
 assert(settings_branch_target(0x23b143c,0)==0);
 assert(settings_branch_target(0x2714dd0,0x4a6eb6e8)==0xe004b8);
 settings_load();assert(!settings_loaded&&settings_reads==0&&speed==1);
 pink_enabled=1;speed=0;country_choice=2;language_choice=2;settings_changed();
 for(int i=0;i<44;i++)settings_tick();assert(settings_writes==0);settings_tick();assert(settings_writes==1);
 settings_loaded=0;pink_enabled=0;speed=1;country_choice=language_choice=0;settings_retry=0;settings_tick();
 assert(pink_enabled==1&&speed==0&&country_choice==2&&language_choice==2);
 pink_enabled=0;settings_changed();settings_save();assert(settings_sequence==2);
 disk[0][7]^=1;settings_loaded=0;pink_enabled=0;settings_load();assert(pink_enabled==1&&settings_sequence==1);
 u32 before=settings_sequence;fail_write=1;settings_changed();settings_save();assert(settings_sequence==before&&settings_errors==1&&settings_dirty);
 u32 invalid[8];memcpy(invalid,disk[1],32);invalid[5]=999;invalid[7]=settings_checksum(invalid);assert(!settings_valid(invalid));
 puts("Options journal restart, debounce, checksum, corrupt-slot recovery and failed-write retention passed");return 0;
}
