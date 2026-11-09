/* Pure wire mapping: native course arrays and ghost payloads remain untouched. */
#ifndef CTGP_TT_WIRE_H
#define CTGP_TT_WIRE_H
#include "tt_category.h"
#include "wire_catalog.h"
static unsigned ctgp_tt_wire_slot(const struct CtgpTTCategory *category){
 if(!category||!category->track||(category->cc!=150&&category->cc!=200)||category->pink>1)return 0;
 for(unsigned i=0;i<CTGP_TT_WIRE_COUNT;i++){
  const struct CtgpTTWireTrack *row=&ctgp_tt_wire_tracks[i];
  if(ctgp_tt_equal(row->id,category->track->id)&&ctgp_tt_equal(row->revision,category->track->revision))
   return row->base+(category->cc==200?1:0)+(category->pink?2:0);
 }
 return 0;
}
static unsigned ctgp_tt_wire_category(const struct CtgpTTCategory *category,unsigned native){
 /* Standard Nintendo 150cc boards remain compatible with native records. */
 if(category&&category->track&&!category->pink&&category->cc==150&&
    category->track->id&&category->track->id[0]=='n')return native;
 unsigned slot=ctgp_tt_wire_slot(category);
 return slot?slot+16:0;
}
#endif
