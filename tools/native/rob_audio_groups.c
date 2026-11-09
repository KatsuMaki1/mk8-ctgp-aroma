/* The native group table has IDs0..36. R.O.B.'s actor/bank stays independent. */
typedef unsigned int u32;
extern u32 original_audio_groups(u32,const u32*);
const char rob_audio_groups_marker[]="MK8_ROB_NATIVE_GROUP_ALIAS_V1";
volatile u32 rob_audio_groups_aliases;
u32 rob_audio_groups(u32 manager,const u32 *driver){
    if(driver && *driver==37){
        const u32 donor=28;
        rob_audio_groups_aliases++;
        return original_audio_groups(manager,&donor);
    }
    return original_audio_groups(manager,driver);
}
