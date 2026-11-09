/* Lobby/globe country fix: write the Options country ONLY into the local player's entry of the player list (ctx+0x2C0).
 * The earlier test "entry+0xB0 bit 0x20" is set for every online player, so in a room each client stamped its own country on all players.
 * Measured on two live clients: entry+0x34 == 0xFFFFFFFF for the remote player and 0 for the local one (entry+0x28 == 2 for local, 0 for remote). */
typedef unsigned int u32;
typedef unsigned char u8;
#define W(p,o) (*(volatile u32 *)((__UINTPTR_TYPE__)(p)+(o)))
#define B(p,o) (*(volatile u8 *)((__UINTPTR_TYPE__)(p)+(o)))
const char globe_fix_marker[]="CTGP_GLOBE_FIX_V1";
volatile u32 globe_fix_calls,globe_fix_patched,globe_fix_skipped_remote;
typedef u32(*Original)(u32,u32,u32,u32,u32,u32,u32,u32);

static int local_country(u32 *count_out){
 u32 country=((u32(*)(void))(__UINTPTR_TYPE__)GLOBE_SELECTED_COUNTRY)();
 u32 ctx=((u32(*)(void))(__UINTPTR_TYPE__)0x024ce59cu)();
 *count_out=0;if(!ctx)return -1;
 u32 list=W(ctx,0x2c0);if(!list)return -1;
 u32 count=W(list,0x34),data=W(list,0x3c);if(!data||count>32)return -1;
 *count_out=count;int self=-1;
 for(u32 i=0;i<count;i++){
  u32 entry=W(data,i*4);if(!entry||!(W(entry,0xb0)&0x20))continue;
  /* A remote player in a room has entry+0x34 == -1. A lone player (one entry) is always the local one. */
  if(count>1&&W(entry,0x34)==0xffffffffu){globe_fix_skipped_remote++;continue;}
  if(country){B(entry,0x124)=(u8)country;W(entry,0xb0)|=4;globe_fix_patched++;}
  if(self<0)self=(int)i;
 }
 return self;
}
/* Same contract as the previous globe_plate hook: setPlayer(this, playerInfo, index); an index outside the list reads a null entry (no flag). */
u32 globe_fix_plate(u32 a,u32 b,u32 c,u32 d,u32 e,u32 f,u32 g,u32 h){
 u32 count;int self=local_country(&count);
 globe_fix_calls++;
 if(((u32(*)(void))(__UINTPTR_TYPE__)GLOBE_SELECTED_COUNTRY)()&&self>=0&&c>=count)c=(u32)self;
 return ((Original)(__UINTPTR_TYPE__)GLOBE_ORIGINAL)(a,b,c,d,e,f,g,h);
}
