#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "../tools/native/game_options.c"
void original_format0(u32 a,u32 b,const struct String*c){(void)a;(void)b;(void)c;}
void original_format1(u32 a,u32 b,const struct String*c){(void)a;(void)b;(void)c;}
void original_format2(u32 a,u32 b,const struct String*c){(void)a;(void)b;(void)c;}
void original_create(u32 a){(void)a;}
void original_event(u32 a,u32 b){(void)a;(void)b;}
void original_hud(u32 a){(void)a;}
int main(void) {
    struct String out,p={"mapobj/VRfair/VRfair.bfres",123};
    assert(route(&p,&out)==&p);
    struct String dark_path={"course/Gu_DarkSanctuaryWiiu/course_model.szs",123};
    route(&dark_path,&out);
    assert(dark_course==1);
    const struct String *mapped=route(&p,&out);
    assert(mapped==&out && out.vtable==123);
    assert(strcmp(out.text,"custom/course_assets/Gu_DarkSanctuaryWiiu/mapobj/VRfair/VRfair.bfres")==0);
    struct String other={"mapobj/VRfair/VRfair.bfres.extra",123};
    assert(route(&other,&out)==&other);
    struct String sound={"/mapobj/TikiTak/SNDG_TikiTak.bars",123};
    assert(route(&sound,&out)==&out);
    struct String choco={"/course/Gu_ChocoIsland/course_model.szs",123};
    route(&choco,&out);
    assert(dark_course==0 && route(&p,&out)==&p);
    struct String near_name={"course/Gu_DarkSanctuaryWiiuOther/course_model.szs",123};
    route(&near_name,&out);assert(dark_course==0);
    assert(route(0,&out)==0);
    puts("PASS: course routing, all original names retained, fallback, exact matching and course changes");
    return 0;
}
