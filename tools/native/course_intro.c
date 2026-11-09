/* Match the loaded course directory, not a donor's native course ID. */
typedef unsigned int u32;
struct String {const char *text;u32 vtable;};
#ifndef INTRO_HOST
#define W(p,o) (*(u32*)((__UINTPTR_TYPE__)(p)+(o)))
#define STR(p) ((const char*)(__UINTPTR_TYPE__)(p))
#endif
const char course_intro_marker[]="MK8_CUSTOM_COURSE_INTRO_V1";
static int equal(const char *a,const char *b){if(!a||!b)return 0;while(*a&&*a==*b){a++;b++;}return !*a&&!*b;}
static u32 message(u32 manager,const char *directory,u32 original,u32 tag){
    if(!manager||!directory||!*directory||W(manager,4)>256||!W(manager,8))return original;
    u32 rows=W(manager,8);
    for(u32 i=0;i<W(manager,4);i++) {
        u32 row=rows+i*0x54;
        for(u32 slot=0;slot<4;slot++) {
            u32 dir=W(row,0x34+slot*4);
            if(dir&&equal(STR(dir),directory)) {
                u32 id=W(row,(tag?0x24:0x14)+slot*4);
                return id?id:original;
            }
        }
    }
    return original;
}
#ifndef INTRO_HOST
u32 course_intro(u32 control,const struct String *pane,u32 original){
    u32 id=message(W(0x10302564u,0),STR(COURSE_PATH),original,
        pane&&equal(pane->text,"T_ClassicName_00"));
    return ((u32(*)(u32,const struct String*,u32))0x025367e8u)(control,pane,id);
}
#endif
