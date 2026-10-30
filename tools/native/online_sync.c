/* EUR81 private-room vote metadata, directory and preview correspondence. */
#include "online_resolve.h"
typedef online_u32 u32;
typedef online_u8 u8;
#define W(p,o) (*(u32 *)((u8 *)(__UINTPTR_TYPE__)(p)+(o)))
#define B(p,o) (*(u8 *)((u8 *)(__UINTPTR_TYPE__)(p)+(o)))
#define P(p) ((u8 *)(__UINTPTR_TYPE__)(p))
#ifndef GAME_TEXT_SHIFT
#define GAME_TEXT_SHIFT 0u
#define GAME_DATA_SHIFT 0u
#define CTGP_CODE_BASE 0x02b10000u
#define CTGP_DATA_BASE 0x10300000u
#endif
#define G(a) ((a)+GAME_DATA_SHIFT)
#define C(o) (CTGP_DATA_BASE+(o))
#define CALL(a,t) ((t)(__UINTPTR_TYPE__)((a)+GAME_TEXT_SHIFT))
const char online_marker[]="MK8_ONLINE_SYNC_EUR81_V1";
volatile u32 online_published,online_winners,online_missing,online_previews;
volatile u32 online_received;
volatile u32 online_status,online_course,online_page,online_slot;
volatile u32 online_error_count,online_error_result,online_error_detail,online_error_flags;
extern void original_vote(u32,u32,u32);
extern void original_preview(u32,u32,u32);
extern void original_receive(u32,u32,u32);
extern void original_update(u32);

static u32 get_page(u32 id) {
    u32 engine=W(G(0x1018a18c),0);
    if(!engine)return 0;
    u32 pages=W(engine,0x10);
    if(!pages || W(pages,0)<=id || !W(pages,4))return 0;
    return W(W(pages,4),4*id);
}
static u32 menu_data(u32 menu) {
    if(!menu || !W(menu,0))return 0;
    return ((u32 (*)(u32))(__UINTPTR_TYPE__)W(W(menu,0),0x15c))(menu);
}
static u32 course_extension(u32 page) {
    if(!page)return 0;
    return ((u32 (*)(u32))(__UINTPTR_TYPE__)(CTGP_CODE_BASE+0x5c70))(page);
}
static u32 native_menu(void) {
    u32 net=CALL(0x023d44f0,u32 (*)(void))();
    return net?W(net,0x12c):0;
}
static u32 course_rows(void) {
    u32 engine=W(G(0x1018a18c),0);
    if(!engine)return 0;
    u32 models=W(engine,0xc);
    if(!models || W(models,0)<=3 || !W(models,4))return 0;
    u32 model=W(W(models,4),12);
    return model?W(model,0x28):0;
}
static u32 player_page(u32 identity,u32 *page) {
    u32 transport=W(C(0x2590),0);
    if(!transport)return 0;
    for(u32 i=0;i<12;i++) {
        u32 record=transport+0x2c+12*i;
        if(W(record,0)!=0xfd && online_same_player(P(record),P(identity))) {
            *page=W(record,8);return 1;
        }
    }
    return 0;
}
static u32 resolve(u32 identity,u32 course,u32 *slot,u32 *page) {
    u32 rows=course_rows(),cup,manager=W(C(0x2564),0);
    if(!rows || !manager || !player_page(identity,page))return 0;
    if(!online_course_position(P(rows),course,&cup,slot))return 0;
    return (u32)(__UINTPTR_TYPE__)online_find_cup(P(W(manager,8)),W(manager,4),*page,cup);
}

/* Publish beside native setVote rather than depending on UI event numbers. */
void online_vote(u32 menu,u32 course,u32 flags) {
    original_vote(menu,course,flags);
    if(!B(C(0x2594),0))return;
    u32 page=course_extension(get_page(63)),transport=W(C(0x2590),0);
    u32 framework=W(G(0x101a8ec4),0),data=menu_data(menu);
    if(!page || !transport || !framework || !data)return;
    u32 peer=W(framework,0x10);
    if(!peer || !W(peer,0x64))return;
    u32 group=((u32 (*)(u32,u32))(__UINTPTR_TYPE__)W(W(peer,0x64),0xd4))(peer,peer+4);
    if(!group || W(group,0)>2 || !W(group,8))return;
    for(u32 i=0;i<W(group,0);i++) {
        u32 uid=W(W(group,8),4*i),dest=0;
        if(!uid || W(uid,0)==0xfd)continue;
        for(u32 j=0;j<12;j++) {
            u32 r=transport+0x2c+j*12;
            if(online_same_player(P(r),P(uid))) {dest=r;break;}
            if(!dest && W(r,0)==0xfd)dest=r;
        }
        if(!dest)continue;
        for(u32 k=0;k<6;k++)B(dest,k)=B(uid,k);
        B(dest,6)=B(dest,7)=0;
        W(dest,8)=W(page,0x20);
        online_published++;
    }
}

int online_winner(u32 menu) {
    int result=CALL(0x02412318,int (*)(u32))(menu);
    if(result<0 || !B(C(0x2594),0))return result;
    u32 data=menu_data(menu),slot,page;
    if(!data)return result;
    const u8 *vote=online_winning_vote(P(data));
    if(!vote) {online_status=7;return result;}
    u32 course=vote[8]>>1;
    online_course=course;
    if(!player_page(data+0x90,&page)) {online_missing++;online_status=2;return result;}
    online_page=page;
    u32 dir;
    if(page==0) {
        u32 cup,rows=course_rows();
        if(!rows || !online_course_position(P(rows),course,&cup,&slot)) {online_status=3;return result;}
        dir=W(C(0x28e8),4*course);
    } else {
        u32 record=resolve(data+0x90,course,&slot,&page);
        if(!record) {online_missing++;online_status=4;return result;}
        dir=W(record,0x34+4*slot);
    }
    online_slot=slot;
    if(!dir || B(dir,0)!='G' || B(dir,1)=='i') {online_missing++;online_status=5;return result;}
    if(W(G(0x101ab678),4*course)==dir) {online_status=6;return result;}
    u32 ui=get_page(63);
    u32 extension=course_extension(ui);
    if(extension) {
        W(extension,0x20)=page;
        ((void (*)(u32,u32))(__UINTPTR_TYPE__)(CTGP_CODE_BASE+0x3a54))(ui,extension);
        ((void (*)(u32,u32))(__UINTPTR_TYPE__)(CTGP_CODE_BASE+0x37ec))(ui,extension);
    }
    W(G(0x101ab678),4*course)=dir;
    online_winners++;
    online_status=6;
    return result;
}

/* Native vote data and the custom page channel can arrive in either order.
   Retry on the UI thread throughout the roulette, before its race transition. */
void online_update(u32 ui) {
    if(B(C(0x2594),0)) {
        u32 menu=native_menu();
        if(menu)online_winner(menu);
    }
    original_update(ui);
}

/* This EUR81 observer callback is a native no-op. Retain that behavior while
   recording the PIA result preceding a generic communication-error dialog. */
void online_error(u32 object,u32 result,u32 detail,u32 flags) {
    (void)object;
    online_error_result=result;online_error_detail=detail;online_error_flags=flags;
    online_error_count++;
}

void online_preview(u32 control,u32 course_ptr,u32 random) {
    original_preview(control,course_ptr,random);
    if(random || !B(C(0x2594),0))return;
    u32 ui=get_page(65),menu=native_menu(),slot,page;
    if(!ui || !menu || W(ui,0x214)>12 || !W(ui,0x21c))return;
    for(u32 i=0;i<W(ui,0x214);i++) {
        if(W(W(ui,0x21c),4*i)!=control)continue;
        u32 record=resolve(menu+0xd8+0x1c*i+4,W(course_ptr,0),&slot,&page);
        if(!record)return;
        u32 texture=W(record,0x44+4*slot);
        if(texture) {
            CALL(0x02531c54,void (*)(u32,u32,u32,u32))(control,W(control,0x58),texture,1);
            online_previews++;
        }
        return;
    }
}

/* Record delivery without invoking UI functions from a transport callback. */
void online_receive(u32 transport,u32 peer,u32 packet) {
    original_receive(transport,peer,packet);
    online_received++;
}
