/* Message IDs are unique across the four EUR MSBT archives (builder checks it).
 * Override only messages that exist in the original manager. Keep unknown IDs
 * and native expansion/control codes intact. Fonts and loaded picture labels
 * are not rebuilt while a page is alive; fresh pages use the selected locale. */
struct LocalMessage {u32 id;const u16 *text;};
struct LocalLanguage {
 const char *code;const u16 *name,*country,*automatic,*language,*speed,*on,*off;
 const u16 *const *countries;const struct LocalMessage *messages;u32 count;
};
#include "options_catalog.h"
#define COUNTRY_COUNT (sizeof(country_ids)/sizeof(country_ids[0]))
#define LANGUAGE_COUNT (sizeof(languages)/sizeof(languages[0]))
extern const char *original_language_code(void);
extern const u16 *original_language_message(u32,u32);
static u32 language_choice;
static u32 language_epoch=1,language_saved_object,language_saved_region,language_saved_id;
static void language_set(u32 choice){
 if(choice>LANGUAGE_COUNT)return;
 language_choice=choice;language_epoch++;
 u32 ctx=FN(0x24ce59c,u32(*)(void))();u32 locale=ctx?W(ctx,0x2d0):0;
 if(!locale)return;
 if(!choice){
  if(locale==language_saved_object){W(locale,4)=language_saved_region;W(locale,8)=language_saved_id;}
  language_saved_object=0;return;
 }
 if(locale!=language_saved_object){language_saved_object=locale;language_saved_region=W(locale,4);language_saved_id=W(locale,8);}
 /* EUR locale matrix at1018A30C: English, French, German, Spanish,
  * Italian, Portuguese, Dutch, Russian. Only game RAM is changed. */
 static const u32 ids[]={1,3,7,2,6,4,5,8};
 W(locale,4)=2;W(locale,8)=ids[choice-1];
}
static u32 language_index(void){
 if(language_choice&&language_choice<=LANGUAGE_COUNT)return language_choice-1;
 const char *code=original_language_code();
 if(code)for(u32 i=0;i<LANGUAGE_COUNT;i++)if(code[0]==languages[i].code[0]&&code[1]==languages[i].code[1])return i;
 return 0;
}
const char *language_code(void){return language_choice?languages[language_index()].code:original_language_code();}
const u16 *language_message(u32 manager,u32 id){
 const u16 *native=original_language_message(manager,id);
 if(!language_choice||!native)return native;
 const struct LocalLanguage *l=&languages[language_index()];u32 low=0,high=l->count;
 while(low<high){u32 mid=low+(high-low)/2;if(l->messages[mid].id<id)low=mid+1;else high=mid;}
 return low<l->count&&l->messages[low].id==id?l->messages[low].text:native;
}
static void option_text(u32 control,const u16 *prefix,const u16 *value,u32 arrows){
 u16 text[128];u32 n=0;
 while(*prefix&&n<75)text[n++]=*prefix++;
 text[n++]=' ';text[n++]=':';text[n++]=' ';
 if(arrows){text[n++]=0x2039;text[n++]=' ';}
 while(*value&&n<123)text[n++]=*value++;
 if(arrows){text[n++]=' ';text[n++]=0x203a;}text[n]=0;
 struct String name={"T_BtnText_00",0x100e10f8};
 if(control)FN(0x2536888,void(*)(u32,const struct String*,const u16*))(control,&name,text);
}
static void language_label(u32 control){
 const struct LocalLanguage *l=&languages[language_index()];
 option_text(control,l->language,language_choice?l->name:l->automatic,1);
}
static u32 cycle_choice(u32 value,u32 count,int direction){return direction<0?(value?value-1:count-1):(value+1)%count;}
