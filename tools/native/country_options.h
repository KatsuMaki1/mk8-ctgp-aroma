/* IDs and translated names are generated from the owned system country.txt. */
static u32 country_choice;
extern u32 original_country_get(u32,u32);
extern u32 original_country_local_get(u32,u32);
volatile u32 country_apply_count,country_local_reads,country_override_reads;
static u32 selected_country(void){return country_ids[country_choice];}
/* The account (account.dat / NNAS) is no longer the source of the country: every native nn::act::GetSimpleAddressId
 * call returns the Options choice while one is selected (country byte in the top 8 bits, no subdivision). */
volatile u32 act_simple_calls,act_simple_ex_calls;
u32 act_simple_address_id(void){
 u32 native=FN(0x2b08b90,u32(*)(void))(),country=selected_country();act_simple_calls++;
 return country?(country<<24):native;
}
int act_simple_address_id_ex(u32 out,u32 slot){
 int result=FN(0x2b08b88,int(*)(u32,u32))(out,slot);u32 country=selected_country();act_simple_ex_calls++;
 if(country&&result>=0)W(out,0)=country<<24;
 return result;
}
static void country_apply(void){
 /* Never encode a country id into opaque player/controller state. Those old
  * +0x74/+0x80/+0x9c8 writes were unverified and bypassed the country accessors.
  * The nn::act hooks, country getters and verified globe nameplate override
  * already supply the chosen country without modifying controller settings. */
 country_apply_count++;
}

u32 country_get(u32 manager,u32 player){
 /* Legacy name retained for build compatibility. 024CB344 is consumed by
  * the steering-usage statistics, NOT by country flag rendering. */
 return original_country_get(manager,player);
}
u32 country_local_get(u32 manager,u32 entry){
 country_local_reads++;
 return original_country_local_get(manager,entry);
}
static void country_label(u32 control){
 const struct LocalLanguage *l=&languages[language_index()];
 option_text(control,l->country,l->countries[country_choice],1);
}

/* Trace of the native national-flag texture lookup 0255DEE4(resourceOwner, countryId): the last 8 calls. */
extern u32 original_flag_texture(u32,u32);
volatile u32 flag_trace_count;
volatile u32 flag_trace[8][2];
u32 flag_texture(u32 owner,u32 id){
 u32 result=original_flag_texture(owner,id);
 flag_trace[flag_trace_count&7][0]=id;flag_trace[flag_trace_count&7][1]=result;flag_trace_count++;
 return result;
}

/* Trace of pane visibility changes on the national-flag / no-flag name panes: who (caller LR) sets what. */
extern void original_set_visible_trace(u32,u32,u32);
volatile u32 vis_trace_count;
volatile u32 vis_trace[16][4];
static int vis_pane_is(u32 pane,const char *prefix,u32 n){
 for(u32 i=0;i<n;i++)if(B(pane,0x80+i)!=(u8)prefix[i])return 0;
 return 1;
}
void set_visible_trace(u32 control,u32 pane,u32 visible){
 if(pane>=0x10000000u&&pane<0x60000000u&&(vis_pane_is(pane,"P_NationalFlag_",15)||vis_pane_is(pane,"T_NameNoFlag_",13))){
  u32 i=vis_trace_count&15;
  vis_trace[i][0]=(u32)(__UINTPTR_TYPE__)__builtin_return_address(0);vis_trace[i][1]=pane;vis_trace[i][2]=visible;vis_trace[i][3]=B(pane,0x80+2);
  vis_trace_count++;
 }
 original_set_visible_trace(control,pane,visible);
}

/* Who sets layout animation frames: unique (caller LR, animation array, index) keys with the latest frame and a hit count.
 * 0253 0EE0(frame, array, index) is called for every animated pane; the newest 48 distinct keys are kept. */
extern void original_anim_frame_trace(double,u32,u32);
volatile u32 anim_trace_next;
volatile u32 anim_trace[48][5];
void anim_frame_trace(double frame,u32 array,u32 index){
 u32 lr=(u32)(__UINTPTR_TYPE__)__builtin_return_address(0),i=0;
 for(;i<48;i++)if(anim_trace[i][0]==lr&&anim_trace[i][1]==array&&anim_trace[i][2]==index)break;
 if(i==48){i=anim_trace_next%48;anim_trace_next++;anim_trace[i][0]=lr;anim_trace[i][1]=array;anim_trace[i][2]=index;anim_trace[i][4]=0;}
 anim_trace[i][3]=(u32)(int)frame;anim_trace[i][4]++;
 original_anim_frame_trace(frame,array,index);
}

/* The globe name bubble copies its country from the player list at ctx+0x2c0: entry+0xB0 bit2 (rlwinm 30,31,31) = "country valid",
 * entry+0x124 = country id, otherwise -1 (no flag). The local player's entry is the one with bit5 (0x20) set in
 * entry+0xB0. Before the bubble code (025145FC) reads it, write the Options country into that entry. */
extern u32 original_globe_plate(u32,u32,u32,u32,u32,u32,u32,u32);
volatile u32 globe_plate_calls,globe_plate_patched,globe_plate_index,globe_plate_count,globe_plate_self,globe_plate_result;
/* Returns the list size and the index of the local player's entry (-1 if none). */
static int globe_self_country(u32 *count_out){
 u32 country=selected_country(),ctx=FN(0x24ce59c,u32(*)(void))();
 *count_out=0;if(!ctx)return -1;
 u32 list=W(ctx,0x2c0);if(!list)return -1;
 u32 count=W(list,0x34),data=W(list,0x3c);if(!data||count>32)return -1;
 *count_out=count;int self=-1;
 for(u32 i=0;i<count;i++){
  u32 entry=W(data,i*4);if(!entry||!(W(entry,0xb0)&0x20))continue;
  if(country){B(entry,0x124)=country;W(entry,0xb0)|=4;globe_plate_patched++;}
  if(self<0)self=(int)i;
 }
 return self;
}
/* setPlayer(this, playerInfo, index): an index outside the list makes the native code read a null entry (country -1). */
u32 globe_plate(u32 a,u32 b,u32 c,u32 d,u32 e,u32 f,u32 g,u32 h){
 u32 count;int self=globe_self_country(&count);
 globe_plate_calls++;globe_plate_index=c;globe_plate_count=count;globe_plate_self=(u32)self;
 if(selected_country()&&self>=0&&c>=count)c=(u32)self;
 u32 result=original_globe_plate(a,b,c,d,e,f,g,h);
 globe_plate_result=W(a,0x290);
 return result;
}
