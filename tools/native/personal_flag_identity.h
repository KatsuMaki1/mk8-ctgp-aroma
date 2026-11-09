/* StoreData system/creator identity; exclude display name and appearance. */
static int personal_flag_same_identity(const unsigned char *recorded,const unsigned char *active){
 unsigned nonzero=0;
 for(unsigned i=4;i<24;i++){unsigned a=recorded[i];nonzero|=a;if(a!=active[i])return 0;}
 return !!nonzero;
}
