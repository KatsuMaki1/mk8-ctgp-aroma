#include <assert.h>
#include "tt_wire.h"
int main(void){
 unsigned used[1024]={0};
 for(unsigned i=0;i<CTGP_TT_WIRE_COUNT;i++){
  const struct CtgpTTWireTrack *row=&ctgp_tt_wire_tracks[i];
  struct CtgpTTTrack track={"unused",row->id,row->revision};
  for(unsigned variant=0;variant<4;variant++){
   struct CtgpTTCategory category={&track,variant&1?200:150,variant>>1};
   unsigned slot=ctgp_tt_wire_slot(&category);
   assert(slot>=128&&slot<1024&&!used[slot]);used[slot]=1;
   unsigned wire=ctgp_tt_wire_category(&category,29);
   assert(wire==((row->id[0]=='n'&&!variant)?29:slot+16));
  }
 }
 struct CtgpTTTrack unknown={"unused","ct.unknown","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"};
 struct CtgpTTCategory category={&unknown,200,0};
 assert(!ctgp_tt_wire_slot(&category));assert(!ctgp_tt_wire_category(&category,29));
 category.cc=100;assert(!ctgp_tt_wire_slot(&category));
 return 0;
}
