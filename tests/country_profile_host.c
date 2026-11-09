#include <assert.h>
#include "country_profile.h"
int main(void){
 unsigned char profile[0xd4];for(unsigned i=0;i<sizeof profile;i++)profile[i]=(unsigned char)i;
 ctgp_profile_country(profile,128);
 for(unsigned i=0;i<sizeof profile;i++){
  unsigned char expected=(i==0x74||i==0x78)?128:(i==0x75||i==0x79)?0:(unsigned char)i;
  assert(profile[i]==expected);
 }
 ctgp_profile_country(profile,0);assert(profile[0x74]==128);
 ctgp_profile_country(profile,256);assert(profile[0x74]==128);
 assert(!ctgp_profile_local_network(profile,219,0x12345678));assert(profile[0x74]==128);
 assert(ctgp_profile_local_network(profile,219,0x02406430));assert(profile[0x74]==219&&profile[0x78]==219);
 assert(ctgp_profile_local_network(profile,1,0x024064f8));assert(profile[0x74]==1&&profile[0x78]==1);
 assert(ctgp_profile_row_country(219,123,123,0)==219);
 assert(ctgp_profile_row_country(219,123,124,77)==77);
 assert(ctgp_profile_row_country(0,123,123,77)==77);
 assert(ctgp_profile_row_country(219,0,0,77)==77);
 return 0;
}
