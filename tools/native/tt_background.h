/* Native menu picture only: no particle/GPU hooks or texture editing. */
static u32 tt_background_allowed;
volatile u32 tt_background_red,tt_background_updates;
volatile u32 tt_graph_bars,tt_graph_updates;
static struct {u32 pane;u8 rgb[12];} tt_graph_original[10];
static u32 tt_graph_page;
static u32 tt_background_active(void){return tt_background_allowed&&W(0x1030c010u,0)&&W(0x1030c000u,0)==3;}
static void tt_graph_update(u32 page){
 if(W(page,4)!=46)return;
 if(tt_graph_page!=page){tt_graph_page=page;for(u32 i=0;i<10;i++)tt_graph_original[i].pane=0;}
 u32 count=W(page,0x20),array=W(page,0x28),bars=0,active=tt_background_active();
 if(count>128||!array)return;
 for(u32 i=0;i<count;i++){
  u32 control=W(array,i*4);if(!control)continue;
  u32 picture=pane(control,"P_GhostVolume_00");if(!picture)continue;
  u32 table=W(picture,8),setter=table?W(table,0x44):0;
  /* Verified native Picture::SetVtxColorElement writes one byte at +a8+index.
   * Reject other pane types; preserve every alpha byte and native graph height. */
  if(setter!=0x02696054u)continue;
  u32 slot=10;
  for(u32 j=0;j<10;j++)if(tt_graph_original[j].pane==picture){slot=j;break;}
  if(slot==10)for(u32 j=0;j<10;j++)if(!tt_graph_original[j].pane){
   slot=j;tt_graph_original[j].pane=picture;
   for(u32 vertex=0;vertex<4;vertex++)for(u32 channel=0;channel<3;channel++)
    tt_graph_original[j].rgb[vertex*3+channel]=B(picture,0xa8+vertex*4+channel);
   break;
  }
  if(slot==10)continue;
  for(u32 vertex=0;vertex<4;vertex++)for(u32 channel=0;channel<3;channel++){
   static const u8 red[3]={180,0,40};
   u32 value=active?red[channel]:tt_graph_original[slot].rgb[vertex*3+channel];
   FN(setter,void(*)(u32,u32,u32))(picture,vertex*4+channel,value);
  }
  bars++;
 }
 tt_graph_bars=bars;tt_graph_updates++;
}
extern void original_tt_background_calc(u32);
extern void previous_tt_background_class_calc(u32);
void tt_background_class_calc(u32 page){
 previous_tt_background_class_calc(page);
 tt_background_allowed=!!W(0x1030c010u,0); /* guarded baseline TT choosing_tt */
}
void tt_background_calc(u32 page){
 original_tt_background_calc(page);
 u32 control=W(page,0xc8);
 if(!control)return;
 u32 red=pane(control,"P_CTGPRedBG_00");
 if(!red)return; /* Old resources remain safe. */
 u32 active=tt_background_active();
 visible(control,"P_CTGPRedBG_00",active);
 visible(control,"P_BlueBG_00",!active);
 tt_background_red=active;tt_background_updates++;
}
