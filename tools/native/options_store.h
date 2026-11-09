/* Independent settings journal: two alternating SD configuration files. */
static u32 settings_loaded,settings_dirty,settings_sequence,settings_retry;
volatile u32 settings_reads,settings_writes,settings_errors,settings_last_stage;
volatile int settings_last_result;
static u32 settings_checksum(const u32 *v){u32 h=2166136261u;for(u32 i=0;i<7;i++)h=(h^v[i])*16777619u;return h;}
static u32 settings_language_id(u32 choice){
 if(!choice)return 0;
 const char *s=languages[choice-1].code;return ((u32)(u8)s[0]<<8)|(u8)s[1];
}
static int settings_valid(const u32 *v){
 if(v[0]!=0x43544f50u||v[1]!=1||v[3]>1||v[4]>1||v[7]!=settings_checksum(v))return 0;
 u32 c=0,l=v[6]==0;
 for(u32 i=0;i<COUNTRY_COUNT;i++)if(country_ids[i]==v[5])c=1;
 for(u32 i=1;i<=LANGUAGE_COUNT;i++)if(settings_language_id(i)==v[6])l=1;
 return c&&l;
}
static inline u32 settings_branch_target(u32 address,u32 word){
 if(word>>26!=18||(word&2)!=0)return 0;
 int delta=(int)(word&0x3fffffc);if(delta&0x2000000)delta-=0x4000000;
 return address+delta;
}
#ifndef OPTIONS_STORE_TEST
/* The loader rewrites imported branches to platform-specific thunks.
 * Decode the relocated call, never call the placeholder stub in the RPX. */
static u32 settings_import(u32 address){return settings_branch_target(address,W(address,0));}
static u8 settings_client[0x1700] __attribute__((aligned(64)));
static u8 settings_command[0xa80] __attribute__((aligned(64)));
static u8 settings_mount_source[0x300] __attribute__((aligned(64)));
static char settings_mount_path[128];
static u32 settings_sd_ready;
static u32 settings_io[8] __attribute__((aligned(64)));
static int settings_transfer(u32 slot,u32 *words,u32 write){
 int result=-1,handle=-1;
 u32 add=settings_import(0x23b143c),init=settings_import(0x23b1444),open=settings_import(0x26cb59c),
  read=settings_import(0x26cb8d8),write_api=settings_import(0x2714dd0),close=settings_import(0x249f5dc),
  flush=settings_import(0x2714dfc),del=settings_import(0x2714af8),mount_source=settings_import(0x272992c),mount=settings_import(0x2729950);
 if(!add||!init||!open||!read||!write_api||!close||!flush||!del||!mount_source||!mount){settings_last_stage=1;settings_last_result=-100;return 0;}
 settings_last_stage=2;settings_last_result=FN(add,int(*)(void*,u32))(settings_client,0);if(settings_last_result<0)return 0;
 FN(init,void(*)(void*))(settings_command);
 if(!settings_sd_ready){
  if(FN(mount_source,int(*)(void*,void*,u32,void*,u32))(settings_client,settings_command,0,settings_mount_source,0)>=0){
   int mounted=FN(mount,int(*)(void*,void*,void*,char*,u32,u32))(settings_client,settings_command,settings_mount_source,settings_mount_path,sizeof(settings_mount_path),0);
   if(mounted>=0||mounted==-5)settings_sd_ready=1;
  }
 }
 const char *path=slot?"/vol/external01/ctgp-options1.bin":"/vol/external01/ctgp-options0.bin";
 settings_last_stage=3;settings_last_result=FN(open,int(*)(void*,void*,const char*,const char*,int*,u32))
    (settings_client,settings_command,path,write?"w":"r",&handle,0);
 if(settings_last_result>=0){
  if(write)for(u32 i=0;i<8;i++)settings_io[i]=words[i];
  result=FN(write?write_api:read,int(*)(void*,void*,void*,u32,u32,int,u32,u32))
   (settings_client,settings_command,settings_io,1,32,handle,0,0);
  settings_last_stage=4;settings_last_result=result;
  int closed=FN(close,int(*)(void*,void*,int,u32))(settings_client,settings_command,handle,0);
  if(closed<0)result=-1;
  if(write&&result==32)FN(flush,int(*)(void*,void*,const char*,u32))(settings_client,settings_command,"/vol/external01",0);
  if(!write&&result==32)for(u32 i=0;i<8;i++)words[i]=settings_io[i];
 }
 FN(del,int(*)(void*,u32))(settings_client,0);
 return result==32;
}
#else
extern int settings_transfer(u32,u32*,u32);
#endif
static void settings_load(void){
 if(settings_loaded)return;
 u32 a[8],b[8],*best=0;
 if(settings_transfer(0,a,0)&&settings_valid(a))best=a;
 if(settings_transfer(1,b,0)&&settings_valid(b)&&(!best||(int)(b[2]-best[2])>0))best=b;
 if(!best)return;
 settings_loaded=1;settings_sequence=best[2];W(0x10305000,0)=best[3];pink_enabled=best[4];
 for(u32 i=0;i<COUNTRY_COUNT;i++)if(country_ids[i]==best[5])country_choice=i;
 u32 choice=0;for(u32 i=1;i<=LANGUAGE_COUNT;i++)if(settings_language_id(i)==best[6])choice=i;
 language_set(choice);country_apply();settings_reads++;
}
static void settings_save(void){
 if(!settings_dirty)return;
 u32 v[8]={0x43544f50u,1,settings_sequence+1,!!W(0x10305000,0),!!pink_enabled,country_ids[country_choice],settings_language_id(language_choice),0};
 v[7]=settings_checksum(v);
 if(settings_transfer(v[2]&1,v,1)){settings_sequence=v[2];settings_dirty=0;settings_writes++;}
 else{settings_errors++;settings_dirty=120;}
}
static void settings_changed(void){settings_loaded=1;settings_dirty=45;}
static void settings_tick(void){
 if(!settings_loaded){if(settings_retry)settings_retry--;else{settings_load();settings_retry=60;}}
 if(settings_dirty&&!--settings_dirty){settings_dirty=1;settings_save();}
}
