#include <assert.h>
#include "../tools/native/rob_audio_groups.c"
static u32 seen;
u32 original_audio_groups(u32 manager,const u32 *driver){assert(manager==123);seen=driver?*driver:99;return 456;}
int main(void){
 for(u32 i=0;i<37;i++){assert(rob_audio_groups(123,&i)==456);assert(seen==i);}
 u32 rob=37;assert(rob_audio_groups(123,&rob)==456);assert(seen==28 && rob==37 && rob_audio_groups_aliases==1);
 rob_audio_groups(123,0);assert(seen==99);
 return 0;
}
