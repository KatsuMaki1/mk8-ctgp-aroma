/* Native VS selectors; these controls exist only while Options is active. */
#if defined(ENABLE_PINK_DRIFT) || defined(OPTIONS_PINK_ROW)
#define OPTION_ROW_COUNT 4u
#else
#define OPTION_ROW_COUNT 3u
#endif
struct OptionModel {u32 unused;const __UINTPTR_TYPE__ *vtable;u32 index,pad;u8 style;};
static u32 option_rows[OPTION_ROW_COUNT],row_owner,row_page_count,row_nav_count,row_page_end,row_nav_end;
static u32 model_enabled(struct OptionModel *m){(void)m;return 1;}
static u32 model_type(struct OptionModel *m){(void)m;return 5;}
static const u16 *model_label(struct OptionModel *m){
 const struct LocalLanguage *l=&languages[language_index()];
 static const u16 *const labels[]={u"Pink mini-turbo",u"Mini-turbo rose",u"Rosa Mini-Turbo",u"Miniturbo rosa",u"Mini-turbo rosa",u"Miniturbo rosa",u"Roze mini-turbo",u"Розовый мини-турбо"};
 return m->index==3?labels[language_index()]:(m->index==0?l->speed:(m->index==1?l->country:l->language));
}
static u16 row_value[OPTION_ROW_COUNT][96];
static const u16 *model_value(struct OptionModel *m){
 const struct LocalLanguage *l=&languages[language_index()];const u16 *v;
 if(m->index==0)v=W(0x10305000,0)?l->on:l->off;
 else if(m->index==1)v=l->countries[country_choice];
 else if(m->index==3)v=pink_enabled?l->on:l->off;
 else v=language_choice?l->name:l->automatic;
 u32 n=0;while(v[n]&&n<26){row_value[m->index][n]=v[n];n++;}
 if(v[n])row_value[m->index][n++]=0x2026;
 row_value[m->index][n]=0;return row_value[m->index];
}
static void model_change(struct OptionModel *m,const u32 *direction){
 if(!options)return;
 int step=*direction==2?-1:1;
 if(m->index==0)W(0x10305000,0)^=1;
 else if(m->index==1){country_choice=cycle_choice(country_choice,COUNTRY_COUNT,step);country_apply();}
 else if(m->index==3)pink_enabled^=1;
 else{language_set(cycle_choice(language_choice,LANGUAGE_COUNT+1,step));refresh_top();}
 settings_changed();
}
static const __UINTPTR_TYPE__ option_model_vtable[20]={
 [3]=(__UINTPTR_TYPE__)model_enabled,[11]=(__UINTPTR_TYPE__)model_type,
 [13]=(__UINTPTR_TYPE__)model_label,[17]=(__UINTPTR_TYPE__)model_value,
 [19]=(__UINTPTR_TYPE__)model_change
};
static struct OptionModel option_models[4]={{0,option_model_vtable,0,0,0},{0,option_model_vtable,1,0,0},{0,option_model_vtable,2,0,0},{0,option_model_vtable,3,0,0}};
static const char *const row_names[]={"P_OptionRow_00","P_OptionRow_01","P_OptionRow_02","P_OptionRow_03"};
static void reserve_rows(u32 object,u32 countoff,u32 capacityoff,u32 arrayoff){
 u32 count=W(object,countoff);if(count>128||count+OPTION_ROW_COUNT<=W(object,capacityoff))return;
 u32 array=FN(0x2721868,u32(*)(u32))((count+OPTION_ROW_COUNT+1)*4);if(!array)return;
 u32 old=W(object,arrayoff);for(u32 i=0;i<count;i++)W(array,4*i)=W(old,4*i);
 W(object,arrayoff)=array;W(object,capacityoff)=count+OPTION_ROW_COUNT+1;
}
static void create_rows(u32 page,u32 layout){
 if(row_owner==page&&option_rows[0])return;
 row_owner=page;for(u32 i=0;i<OPTION_ROW_COUNT;i++)option_rows[i]=0;
 row_page_count=W(page,0x20);reserve_rows(page,0x20,0x24,0x28);
 u32 manager=W(page,0xac);if(!manager)return;
 row_nav_count=W(manager,0xec);reserve_rows(manager,0xec,0xe4,0xe8);
 for(u32 i=0;i<OPTION_ROW_COUNT;i++){
  u32 row=FN(0x258ae5c,u32(*)(u32))(0);if(!row)return;
  struct String name={row_names[i],0x100e10f8};
  FN(0x253ecf4,void(*)(u32,u32,u32,const struct String*))(page,row,layout,&name);
  W(row,0)=14+i;option_rows[i]=row;
  FN(0x258b2b0,void(*)(u32,struct OptionModel*))(row,&option_models[i]);
 }
 row_page_end=W(page,0x20);row_nav_end=W(manager,0xec);
}
static void rows_active(u32 page,u32 active){
 if(page!=row_owner||!option_rows[OPTION_ROW_COUNT-1]||!row_page_end)return;
 u32 manager=W(page,0xac);if(!manager)return;
 if(!active&&W(manager,0xec)==row_nav_end){
  for(u32 controller=0;controller<4;controller++){
   u32 selected=W(manager,0xc+controller*0x28);
   if(selected>=row_nav_count&&selected<row_nav_end)
    FN(0x25382bc,void(*)(u32,u32,u32,u32,u32))(manager,controller,0,0,1);
  }
 }
 W(page,0x20)=active?row_page_end:row_page_count;
 W(manager,0xec)=active?row_nav_end:row_nav_count;
}
static void update_rows(u32 layout,u32 show){
 for(u32 i=0;i<OPTION_ROW_COUNT;i++){
  visible(layout,row_names[i],show);u32 row=option_rows[i];if(!row||!show)continue;
  visible(row,"N_All_01",0);visible(row,"N_All_00",1);
  visible(row,"T_Text_00",1);visible(row,"T_Text_01",1);
  struct String label_name={"T_Text_00",0x100e10f8},value_name={"T_Text_01",0x100e10f8};
  FN(0x2536888,void(*)(u32,const struct String*,const u16*))(row,&label_name,model_label(&option_models[i]));
  FN(0x2536888,void(*)(u32,const struct String*,const u16*))(row,&value_name,model_value(&option_models[i]));
 }
}
