/* First Cemu prototype. Run only with the independent TT200 test save. */
typedef unsigned int u32;typedef unsigned char u8;
#ifndef W
#define W(p,o) (*(volatile u32 *)((__UINTPTR_TYPE__)(p)+(o)))
#define B(p,o) (*(volatile u8 *)((__UINTPTR_TYPE__)(p)+(o)))
#endif
#ifndef FN
#define FN(a,t) ((t)(__UINTPTR_TYPE__)(a))
#endif
extern void original_tt_mode(u32,u32);
extern void original_tt_class_in(u32);
extern void original_tt_class_calc(u32);
extern void original_tt_class_event(u32,u32);
extern void original_tt_race_copy(u32,u32);
const char tt200_marker[]="MK8_TT200_SANDBOX_P1";
static u32 choosing_tt;
volatile u32 tt200_selected_class=2;
volatile u32 tt200_selection_count;
volatile u32 tt200_mode_count;
volatile u32 tt200_race_copy_count;
void tt200_mode(u32 page,u32 event){
    original_tt_mode(page,event);
    if(!event || !W(event,8) || W(event,0x14)!=2)return;
    choosing_tt=W(event,0xc)==1;tt200_selected_class=2;tt200_mode_count++;
    if(choosing_tt)W(page,0xcc)=30; /* Reuse the native cylinder-class page. */
}
static u32 tt_menu_page,tt_last_focus=2;
static u32 tt_parent[5],tt_parent_y[5];
static void tt_restore_positions(void){
    for(u32 i=0;i<5;i++)if(tt_parent[i])W(tt_parent[i],0x20)=tt_parent_y[i];
}
static void tt_class_layout(u32 page){
    if(page!=tt_menu_page || W(page,0x11c)<5 || !W(page,0x124))return;
    u32 buttons=W(page,0x124);
    for(u32 i=0;i<5;i++){
        u32 button=W(buttons,i*4),layout=button?W(button,0x50):0;
        u32 pane=layout?W(layout,0xc):0,parent=pane?W(pane,0xc):0;
        u32 visible=!choosing_tt || i==2 || i==4;
        if(parent)FN(0x02531bdcu,void(*)(u32,u32,u32))(button,parent,visible);
        if(pane)FN(0x02531bdcu,void(*)(u32,u32,u32))(button,pane,visible);
        if(parent && parent==tt_parent[i]){
            W(parent,0x20)=tt_parent_y[i];
            if(choosing_tt && (i==2 || i==4)){
                union {u32 word;float value;} y;y.word=tt_parent_y[i];
                y.value+=i==2?60.0f:140.0f;W(parent,0x20)=y.word;
            }
        }
    }
}
void tt200_class_calc(u32 page){original_tt_class_calc(page);tt_class_layout(page);}
void tt200_class_in(u32 page){
    if(page==tt_menu_page)tt_restore_positions();
    original_tt_class_in(page);
    if(W(page,0x11c)<5 || !W(page,0x124))return;
    u32 buttons=W(page,0x124),native150=W(buttons,8),native200=W(buttons,16);
    if(!native150 || !native200)return;
    if(choosing_tt){
    /* Keep the 200cc button usable even if GP unlock data would disable it. */
    B(native200,0x18)=B(native150,0x18);
    W(native200,0x38)=(W(native200,0x38)&0x7fffffffu)|(W(native150,0x38)&0x80000000u);
    }
    tt_menu_page=page;tt_last_focus=tt200_selected_class==3?4:2;
    /* +50 is the layout; its +0c holds the root pane (native 02531718). */
    for(u32 i=0;i<5;i++){
        u32 button=W(buttons,i*4),layout=button?W(button,0x50):0;
        u32 pane=layout?W(layout,0xc):0;
        tt_parent[i]=pane?W(pane,0xc):0;
        tt_parent_y[i]=tt_parent[i]?W(tt_parent[i],0x20):0;
    }
    tt_class_layout(page);
    if(!choosing_tt)return;
    FN(0x025382bcu,void(*)(u32,u32,u32,u32,u32))(W(page,0xac),0,tt_last_focus,0,1);
}
void tt200_class_event(u32 page,u32 event){
    if(choosing_tt && event && W(event,8)){
        u32 index=W(event,0xc);
        if(index!=2 && index!=4){
            if(W(event,0x14)==0){
                u32 target=tt_last_focus==2?4:2;
                FN(0x025382bcu,void(*)(u32,u32,u32,u32,u32))(W(page,0xac),0,target,0,1);
            }
            return;
        }
        tt_last_focus=index;
        if(W(event,0x14)==2){
            tt200_selected_class=index==4?3:2;tt200_selection_count++;
        }
    }
    original_tt_class_event(page,event);
}

/* Native race-settings copies can replace the class selected in the UI. */
void tt200_race_copy(u32 destination,u32 source){
    original_tt_race_copy(destination,source);
    if(choosing_tt && destination && W(destination,0x17c)==1){
        W(destination,0x180)=tt200_selected_class;
        B(destination,0x184)=0;
        tt200_race_copy_count++;
    }
}

/* TT setup sets engine class at config+180, using r26=config+1c.
 * Preserve all registers and CR across this in-place store replacement. */
volatile u32 tt200_rule_store_count;
#ifndef TT200_HOST
__asm__(
".text\n.global tt200_tt_rule_store\ntt200_tt_rule_store:\n"
"stwu 1,-16(1)\nstw 0,4(1)\nstw 12,8(1)\nmfcr 0\nstw 0,12(1)\n"
"lis 12,choosing_tt@ha\nlwz 0,choosing_tt@l(12)\ncmpwi 0,0\nbeq 1f\n"
"lis 12,tt200_selected_class@ha\nlwz 0,tt200_selected_class@l(12)\nstw 0,0x164(26)\n"
"lis 12,tt200_rule_store_count@ha\nli 0,1\nstw 0,tt200_rule_store_count@l(12)\nb 2f\n"
"1: stw 31,0x164(26)\n"
"2: lwz 0,12(1)\nmtcrf 255,0\nlwz 12,8(1)\nlwz 0,4(1)\naddi 1,1,16\nb tt200_rule_return\n"
);

#endif
