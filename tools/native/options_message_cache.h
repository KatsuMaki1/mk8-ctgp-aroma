/* Remember native message assignments, then refresh only controls enumerated
 * by a LIVE page. No saved page/control/pane pointer is dereferenced until its
 * owner, control membership and current layout match the native live list. */
extern void original_language_set_default(u32,u32);
extern void original_language_set_named(u32,const struct String*,u32);
extern void original_language_set_pane(u32,u32,u32);
extern void original_language_page_calc(u32);
struct LanguageBinding {u32 control,page,layout,id,pane,kind,epoch;char name[24];};
enum {LANGUAGE_BINDINGS=1024};
static struct LanguageBinding language_bindings[LANGUAGE_BINDINGS];
static u32 language_binding_count,language_refreshing;
static struct {u32 page,epoch;} language_pages[128];
static u32 language_page_count;
volatile u32 language_binding_overflow;
static void language_remember(u32 control,u32 kind,u32 pane_ptr,const char *name,u32 id){
 if(!control||language_refreshing)return;
 u32 page=W(control,4),layout=W(control,0x50);if(!page||!layout)return;
 u32 len=0;if(name){while(name[len]&&len<23)len++;if(name[len])return;}
 u32 i;
 for(i=0;i<language_binding_count;i++){
  struct LanguageBinding *b=&language_bindings[i];
  if(b->control!=control||b->kind!=kind||b->pane!=pane_ptr)continue;
  if(name){u32 j=0;while(j<len&&b->name[j]==name[j])j++;if(j!=len||b->name[len])continue;}
  break;
 }
 if(i==LANGUAGE_BINDINGS){language_binding_overflow++;return;}
 if(i==language_binding_count)language_binding_count++;
 struct LanguageBinding *b=&language_bindings[i];b->control=control;b->page=page;b->layout=layout;
 b->id=id;b->pane=pane_ptr;b->kind=kind;b->epoch=language_epoch;
 for(u32 j=0;j<len;j++)b->name[j]=name[j];
 b->name[len]=0;
}
void language_set_default(u32 control,u32 id){language_remember(control,0,0,0,id);original_language_set_default(control,id);}
void language_set_named(u32 control,const struct String *name,u32 id){language_remember(control,1,0,name?name->text:0,id);original_language_set_named(control,name,id);}
void language_set_pane(u32 control,u32 pane_ptr,u32 id){language_remember(control,2,pane_ptr,0,id);original_language_set_pane(control,pane_ptr,id);}
static void language_refresh_page(u32 page){
 if(!page||language_refreshing)return;
 u32 slot=0;while(slot<language_page_count&&language_pages[slot].page!=page)slot++;
 if(slot<language_page_count&&language_pages[slot].epoch==language_epoch)return;
 u32 count=W(page,0x20),array=W(page,0x28);if(count>128||(!array&&count))return;
 if(slot<128){
  if(slot==language_page_count)language_page_count++;
  language_pages[slot].page=page;language_pages[slot].epoch=language_epoch;
 }
 language_refreshing=1;
 for(u32 i=0;i<count;i++){
  u32 control=W(array,i*4);if(!control)continue;
  for(u32 j=0;j<language_binding_count;j++){
   struct LanguageBinding *b=&language_bindings[j];
   if(b->epoch==language_epoch||b->page!=page||b->control!=control||b->layout!=W(control,0x50))continue;
   b->epoch=language_epoch;
   if(b->kind==0)original_language_set_default(control,b->id);
   else if(b->kind==1){struct String name={b->name,0x100e10f8};original_language_set_named(control,&name,b->id);}
   else original_language_set_pane(control,b->pane,b->id);
  }
 }
 language_refreshing=0;
}
void language_page_calc(u32 page){original_language_page_calc(page);if(W(page,4)==25)settings_tick();language_refresh_page(page);
#ifdef ENABLE_TT_GHOST_SCOPE
 if(W(page,4)==25)tt_scope_ready=0;
#endif
#ifdef ENABLE_TT_RED_BACKGROUND
 tt_graph_update(page);
#endif
}
