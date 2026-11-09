/* Create only this account's private TT directory chain via the SDK SAVE API. */
static u32 settings_import(u32);
static u8 tt_dir_client[0x1700] __attribute__((aligned(64)));
static u8 tt_dir_command[0xa80] __attribute__((aligned(64)));
static u32 tt_save_module,tt_save_mkdir,tt_dirs_api_attempted;
volatile u32 tt_scope_dirs_ready,tt_scope_dir_errors;
volatile int tt_scope_dir_result;
static void tt_ensure_dirs(void){
 if(tt_scope_dirs_ready||tt_scope_slot<1||tt_scope_slot>12)return;
 u32 add=settings_import(0x023b143c),init=settings_import(0x023b1444),del=settings_import(0x02714af8);
 if(!add||!init||!del)return;
 if(!tt_dirs_api_attempted){
  tt_dirs_api_attempted=1;
  u32 acquire=settings_import(0x0249eac8),find=settings_import(0x026789dc);
  if(acquire&&find&&FN(acquire,int(*)(const char*,u32*))("nn_save.rpl",&tt_save_module)>=0)
   FN(find,int(*)(u32,u32,const char*,u32*))(tt_save_module,0,"SAVEMakeDir",&tt_save_mkdir);
 }
 if(!tt_save_mkdir){tt_scope_dir_errors++;tt_scope_dir_result=-100;return;}
 tt_scope_dir_result=FN(add,int(*)(void*,u32))(tt_dir_client,0);
 if(tt_scope_dir_result<0){tt_scope_dir_errors++;return;}
 FN(init,void(*)(void*))(tt_dir_command);
 char path[256];u32 length=0;
 while(tt_scope_personal_path[length]&&length+1<sizeof path){path[length]=tt_scope_personal_path[length];length++;}path[length]=0;
 u32 ok=length&&length<sizeof path-1;
 for(u32 i=1;ok&&i<length;i++)if(path[i]=='/'){
  path[i]=0;
  tt_scope_dir_result=FN(tt_save_mkdir,int(*)(void*,void*,u32,const char*,u32))(tt_dir_client,tt_dir_command,tt_scope_slot,path,0);
  path[i]='/';
  if(tt_scope_dir_result<0&&tt_scope_dir_result!=-5)ok=0;
 }
 FN(del,int(*)(void*,u32))(tt_dir_client,0);
 if(ok)tt_scope_dirs_ready=1;else tt_scope_dir_errors++;
}
