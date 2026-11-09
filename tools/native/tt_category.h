/* Shared TT category contract. Callers supply the SELECTED course, never the last loaded path.
 * This module is not hooked into native record/ranking calls yet. */
#ifndef CTGP_TT_CATEGORY_H
#define CTGP_TT_CATEGORY_H
struct CtgpTTTrack {const char *directory,*id,*revision;};
struct CtgpTTCategory {const struct CtgpTTTrack *track;unsigned cc,pink;};
static int ctgp_tt_equal(const char *a,const char *b){if(!a||!b)return 0;while(*a&&*a==*b){a++;b++;}return !*a&&!*b;}
static int ctgp_tt_select(struct CtgpTTCategory *out,const struct CtgpTTTrack *tracks,unsigned count,const char *directory,unsigned native_class,unsigned pink){
 if(!out)return 0;
 out->track=0;out->cc=0;out->pink=0;
 if(!tracks||!directory||count>4096||(native_class!=2&&native_class!=3)||pink>1)return 0;
 for(unsigned i=0;i<count;i++)if(ctgp_tt_equal(tracks[i].directory,directory)){
  out->track=&tracks[i];out->cc=native_class==3?200:150;out->pink=pink;return 1;
 }
 return 0; /* Unknown custom identity must NOT inherit an official record. */
}
static inline const char *ctgp_tt_rules(const struct CtgpTTCategory *category){
 return category->pink?"ctgp-pink-charge150-boost150-v1":"mk8-u81-native-v1";
}
static int ctgp_tt_append(char *buffer,unsigned capacity,unsigned *used,const char *value){
 if(!value)return 0;
 while(*value){if(*used+1>=capacity)return 0;buffer[(*used)++]=*value++;}
 buffer[*used]=0;return 1;
}
static int ctgp_tt_path(const struct CtgpTTCategory *category,char *buffer,unsigned capacity){
 if(!buffer||!capacity)return 0;
 buffer[0]=0;
 if(!category||!category->track||(category->cc!=150&&category->cc!=200)||category->pink>1)return 0;
 unsigned used=0;
 /* Compact versioned physics suffix keeps native ghost filenames within the
  * game's 256-byte pathname buffers. Full rules IDs remain in server metadata. */
 /* Only the first 8 hex digits of the revision name the directory: Windows (Cemu) rejects paths over
  * 260 characters and the native ghost filename alone is ~118. The full revision stays in server metadata. */
 char revision8[9];unsigned n=0;
 for(;n<8&&category->track->revision&&category->track->revision[n];n++)revision8[n]=category->track->revision[n];
 revision8[n]=0;if(n<8)return 0;
 const char *parts[]={"custom/tt/v1/",category->track->id,"/",revision8,"/",category->cc==200?"200":"150","/",category->pink?"p1":"n1","/"};
 for(unsigned i=0;i<sizeof(parts)/sizeof(parts[0]);i++)if(!ctgp_tt_append(buffer,capacity,&used,parts[i])){buffer[0]=0;return 0;}
 return 1;
}
#endif
