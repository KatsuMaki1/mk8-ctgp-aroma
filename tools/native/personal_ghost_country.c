/* Called ONLY at Ghost page's personal save branch (025C67F4), directly
 * downstream of native GetPersonalRecord 024F2714. Staff/download branches
 * 025C6B5C/025C6E9C retain the native setter and their recorded countries. */
typedef unsigned int u32;
extern u32 personal_country_selected(void);
extern void personal_country_native_set(u32,u32,u32,u32,u32,u32);
const char personal_country_marker[]="CTGP_PERSONAL_CARD_COUNTRY_V2";
volatile u32 personal_country_calls,personal_country_old,personal_country_new;
void personal_country_set(u32 control,u32 name,u32 time,u32 country,u32 parameter,u32 wheel){
 u32 selected=personal_country_selected();
 u32 shown=selected&&selected<=254?selected:country;
 personal_country_calls++;personal_country_old=country;personal_country_new=shown;
 personal_country_native_set(control,name,time,shown,parameter,wheel);
}
