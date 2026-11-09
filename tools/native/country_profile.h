/* Verified 0xD4-byte player profile copied by EUR81 024DD0F0.
 * Native ghost: profile at 0x230; country at 0x2A4 and address at 0x2A8.
 * These are profile bytes, never the controller manager's +0x74/+0x80. */
static void ctgp_profile_country(unsigned char *profile,unsigned country){
 if(!profile||!country||country>255)return;
 profile[0x74]=(unsigned char)country;profile[0x75]=0;
 profile[0x78]=(unsigned char)country;profile[0x79]=0;
}
static inline unsigned ctgp_profile_local_network(unsigned char *profile,unsigned country,unsigned caller){
 if(!profile||!country||country>255||(caller!=0x02406430u&&caller!=0x024064f8u))return 0;
 ctgp_profile_country(profile,country);return 1;
}
/* A personal leaderboard row can be built from an older local ghost whose
 * stored country is zero. Display the current selection for our PID only;
 * do not change the recording or another player's published country. */
static inline unsigned ctgp_profile_row_country(unsigned selected,unsigned self,unsigned row,unsigned recorded){
 return selected&&selected<=255&&self&&self==row?selected:recorded;
}
