/* EUR81 Cemu options panel, independent of race asset hooks. */
typedef unsigned int u32;typedef unsigned short u16;typedef unsigned char u8;
#define W(p,o) (*(volatile u32 *)((u32)(p)+(o)))
#define B(p,o) (*(volatile u8 *)((u32)(p)+(o)))
#define FN(a,t) ((t)(a))
struct String {const char *text;u32 vtable;};
extern void original_panel_create(u32);
extern void original_panel_event(u32,u32);
const char options_panel_marker[]="MK8_OPTIONS_PANEL_V1";
static u32 opened,launcher,toggle,owner;
static const u16 title[]={'+',' ','O','p','t','i','o','n','s',0};
static const u16 on[]={'S','p','e','e','d','o','m','e','t','e','r',' ',':',' ','O','N',0};
static const u16 off[]={'S','p','e','e','d','o','m','e','t','e','r',' ',':',' ','O','F','F',0};
static u32 pane(u32 c,const char *name){struct String n={name,0x100e10f8};return FN(0x02531718,u32(*)(u32,const struct String*))(c,&n);}
static void visible(u32 c,u32 p,u32 v){if(c&&p)FN(0x02531bdc,void(*)(u32,u32,u32))(c,p,v);}
static void text(u32 c,const u16 *value){struct String n={"T_BtnText_00",0x100e10f8};if(c)FN(0x02536888,void(*)(u32,const struct String*,const u16*))(c,&n,value);}
static void focus(u32 page,u32 id){FN(0x025382bc,void(*)(u32,u32,u32,u32,u32))(W(page,0xac),0,id,0,1);}
static void show(u32 page,u32 value){
 opened=value;
 u32 layout=W(page,0x260);
 const char *main[]={"N_Single_00","N_Multi_00","N_OnlineSingle_00","N_OnlineMulti_00","N_MarioKartTV_00","N_Catalog_00","N_Contens_00"};
 for(u32 i=0;i<sizeof(main)/sizeof(main[0]);i++)visible(layout,pane(layout,main[i]),!value);
 visible(layout,pane(layout,"P_Settings_00"),!value);
 visible(layout,pane(layout,"P_OptionSpeed_00"),value);
 visible(layout,pane(layout,"P_OptionsPanel_00"),value);
 visible(layout,pane(layout,"T_OptionsTitle_00"),value);
 visible(layout,pane(layout,"T_OptionsBack_00"),value);
 visible(layout,pane(layout,"P_SettingsIcon_00"),!value);
 text(toggle,W(0x10305000,0)?on:off);
 focus(page,value?14:0);
}
static u32 create(u32 page,const char *part,u32 id){
 u32 c=FN(0x02721868,u32(*)(u32))(0x114);if(!c)return 0;
 for(u32 i=0;i<0x114;i++)B(c,i)=0;
 FN(0x025789b4,u32(*)(u32))(c);W(c,0x54)=0x100d5a2c;W(c,0x64)=0x100d5b34;
 FN(0x02534530,u32(*)(u32))(c+0xf4);W(c,0x24)=3;
 struct String n={part,0x100e10f8};FN(0x0253ecf4,void(*)(u32,u32,u32,const struct String*))(page,c,W(page,0x260),&n);
 W(c,0)=id;W(c,0xd8)=0;return c;
}
void panel_create(u32 page){
 original_panel_create(page);if(W(page,4)!=25)return;
 owner=page;opened=0;launcher=toggle=0;
 u32 count=W(page,0x20),old=W(page,0x28);if(count>128)return;
 if(count+2>W(page,0x24)){
  u32 array=FN(0x02721868,u32(*)(u32))((count+4)*4);if(!array)return;
  for(u32 i=0;i<count;i++)W(array,i*4)=W(old,i*4);
  W(page,0x28)=array;W(page,0x24)=count+4;
 }
 launcher=create(page,"P_Settings_00",13);toggle=create(page,"P_OptionSpeed_00",14);
 text(launcher,title);text(toggle,W(0x10305000,0)?on:off);
 /* The cloned native parts carry a Toad illustration; settings have no character. */
 const char *images[]={"P_Img_00","P_Img_01"};
 for(u32 i=0;i<2;i++){visible(launcher,pane(launcher,images[i]),0);visible(toggle,pane(toggle,images[i]),0);}
 W(page,0x244)|=8;show(page,0);
}
void panel_event(u32 page,u32 event){
 if(page==owner&&W(page,4)==25&&event){
  if(!W(event,8)&&W(event,0)==page+0x230){
   u32 keys=W(event,0x1c);
   if((keys&8)||(opened&&(keys&4))){show(page,!opened);return;}
  }
  if(W(event,8)){
   u32 id=W(event,0xc),kind=W(event,0x14);
   if(id==13){if(kind==2&&!opened)show(page,1);return;}
   if(id==14){if(opened&&kind==2){W(0x10305000,0)^=1;text(toggle,W(0x10305000,0)?on:off);}return;}
   if(opened){if(kind==0)focus(page,14);return;}
  }
  if(opened)return;
 }
 original_panel_event(page,event);
}
