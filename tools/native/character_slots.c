/* Independent driver-slot prototype, EUR81. Does not use costume variant IDs. */
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
#ifndef W
#define W(p,o) (*(volatile u32 *)((u32)(p)+(o)))
#define B(p,o) (*(volatile u8 *)((u32)(p)+(o)))
#define FN(a,t) ((t)(a))
#endif
extern void original_char_create(u32);
extern void original_char_setup(u32);
extern void original_char_available(u32,u32*,const u32*);
extern void original_char_button(u32,const u32*,const u32*);
extern u32 original_char_icon(u32,const u32*,u32);
extern void original_char_name(u32,u32,const u32*,u32);
extern void original_char_finalise(u32,u32);
extern void original_char_texture_name(u32,u32,const u32*,const u32*,u32);
extern void original_char_sound_lookup(u32,u32,const char*);
extern void original_char_audio_init(u32);
extern void original_char_menu_voice(u32,u32);
static u8 rob_menu_selected[4];
volatile u32 character_menu_voice_state[4];
void character_menu_voice(u32 actor,u32 narrator) {
    u32 context=FN(0x021b6e38,u32(*)(u32))(W(actor,0xc));
    u32 player=FN(0x02441d48,u32(*)(u32))(context);
    u32 original=W(actor,0x7c);
    u32 own=player<4 && rob_menu_selected[player];
    character_menu_voice_state[0]=player;character_menu_voice_state[1]=original;
    if(own)W(actor,0x7c)=37;
    character_menu_voice_state[2]=W(actor,0x7c);character_menu_voice_state[3]=own;
    original_char_menu_voice(actor,narrator);
    W(actor,0x7c)=original;
}
volatile u32 character_voice_bank_state[4];
void character_audio_init(u32 actor) {
    original_char_audio_init(actor);
#ifdef ROB_PRIVATE_VOICE
    u32 driver=W(actor,0x20c);
    if(!driver || FN(0x021941a8,u32(*)(u32))(driver)!=37)return;
    character_voice_bank_state[0]=actor;
    character_voice_bank_state[1]=W(actor,0x218);
    FN(0x02056834,void(*)(u32,const char*,u32,u32,u32))(
        actor+0x214,"ROB",W(0x10206328,0),0,0);
    character_voice_bank_state[2]=W(actor,0x218);
    character_voice_bank_state[3]=W(actor,0x220);
#endif
}
/* Read-only host diagnostic: retain requested labels and resolved sound IDs. */
volatile u32 character_voice_trace_count;
struct VoiceTrace {u32 actor,id;char label[88];};
volatile struct VoiceTrace character_voice_trace[12];
void character_sound_lookup(u32 actor,u32 out,const char *label) {
    original_char_sound_lookup(actor,out,label);
    if(!label || label[0]!='p' || label[1]!='V' || label[2]!='O')return;
    u32 n=character_voice_trace_count;
    if(n>=12)return;
    character_voice_trace[n].actor=actor;
    character_voice_trace[n].id=out?W(out,0):0xffffffffu;
    u32 i=0;for(;i<87 && label[i];i++)character_voice_trace[n].label[i]=label[i];
    character_voice_trace[n].label[i]=0;
    character_voice_trace_count=n+1;
}
extern void previous_char_recipe(u32,u32,const u32*);
extern void previous_char_prefix(u32,const char*,u32);
extern u32 previous_char_vehicle_icon(u32,u32,u32,u32,u32);
__attribute__((used)) const char character_slots_marker[]="MK8_INDEPENDENT_ROB_EUR81_V1";
__attribute__((used)) const char character_resource_name[]="ROB";
static u32 pages[16];
static u32 buttons[16][37];
static u32 rob_recipe_scope;
static const u16 rob_name[]={'R','.','O','.','B','.',0};

/* A 37th inline pointer would overwrite live page+0x38c. */
u32 character_button_array(u32 page) {
    for(u32 i=0;i<16;i++) if(pages[i]==page) return (u32)buttons[i];
    for(u32 i=0;i<16;i++) if(!pages[i]) {
        pages[i]=page;
        for(u32 j=0;j<36;j++)buttons[i][j]=W(page,0x2fc+j*4);
        buttons[i][36]=0;
        return (u32)buttons[i];
    }
    /* Native game has six main character-page variants. */
    return 0;
}

void character_create(u32 page) {
    original_char_create(page);
    u32 array=character_button_array(page);
    for(u32 i=0;i<36;i++)W(page,0x2fc+i*4)=W(array,i*4);
}

static u32 heap_at(u32 index) {
    u32 engine=W(0x1018a18c,0), buffer=engine?W(engine,12):0;
    return buffer && W(buffer,0)>index && W(buffer,4)?W(W(buffer,4),index*4):0;
}
struct NativeString {const char *text;u32 vtable;};
static u32 rob_icon(void) {
    u32 heap=heap_at(4),resource=heap?W(heap,4):0;
    struct NativeString name={"ui/cmn/a_menu/timg/tc_Chara_ROB^l.bflim",0x100d25d0};
    return resource?FN(0x0253d47c,u32(*)(u32,const struct NativeString*))(resource,&name):0;
}
u32 character_vehicle_icon(u32 object,u32 kind,u32 id,u32 driver,u32 color) {
    const char *path=0;
    if(kind==0 && driver==37) {
        if(id==0)path="ui/cmn/a_menu/timg/ct_ROB_K_Std^q.bflim";
        if(id==1)path="ui/cmn/a_menu/timg/ct_ROB_K_Skl^q.bflim";
        if(id==14)path="ui/cmn/a_menu/timg/ct_ROB_B_Std^q.bflim";
        if(id==23)path="ui/cmn/a_menu/timg/ct_ROB_V_Atv^q.bflim";
    }
    if(path) {
        u32 heap=heap_at(4),resource=heap?W(heap,4):0;
        struct NativeString name={path,0x100d25d0};
        u32 texture=resource?FN(0x0253d47c,u32(*)(u32,const struct NativeString*))(resource,&name):0;
        if(texture)return texture;
    }
    return previous_char_vehicle_icon(object,kind,id,driver,color);
}

void character_available(u32 page,u32 *out,const u32 *id) {
    if(id && *id==37 && out) {*out=5;return;}
    original_char_available(page,out,id);
}
u32 character_icon(u32 loader,const u32 *id,u32 variant) {
    if(id && *id==37) {u32 texture=rob_icon();if(texture)return texture;u32 donor=28;return original_char_icon(loader,&donor,0);}
    return original_char_icon(loader,id,variant);
}
void character_button(u32 button,const u32 *id,const u32 *state) {
    if(!id || *id!=37) {original_char_button(button,id,state);return;}
    u32 donor=28;
    original_char_button(button,&donor,state);
    W(button,0xf8)=37;
    u32 texture=rob_icon();
    if(texture)FN(0x02531c54,void(*)(u32,u32,u32,u32))(button,W(button,0xfc),texture,0);
}
void character_name(u32 page,u32 player,const u32 *id,u32 variant) {
    if(player<4)rob_menu_selected[player]=id && *id==37;
    if(id && *id==37) {FN(0x025d25b0,void(*)(u32,u32,const u16*))(page,player,rob_name);return;}
    original_char_name(page,player,id,variant);
}
void character_texture_name(u32 loader,u32 out,const u32 *kind,const u32 *id,u32 variant) {
    if(!id || *id!=37 || !kind || *kind>2) {
        original_char_texture_name(loader,out,kind,id,variant);return;
    }
    /* Explicit loose paths also work on screens whose archive predates ROB.
     * The native accessor accepts ui/ paths and caches the loaded texture. */
    static const char *const names[]={"ui/cmn/a_menu/timg/tc_Chara_ROB^l.bflim","ui/cmn/a_common/timg/tc_edChara_ROB^l.bflim","ui/cmn/a_common/timg/tc_MapChara_ROB^l.bflim"};
    u32 buffer=W(out,0),capacity=W(out,8);
    if(!buffer || !capacity)return;
    const char *text=names[*kind];u32 i=0;
    for(;i+1<capacity && text[i];i++)B(buffer,i)=(u8)text[i];
    B(buffer,i)=0;
}

static u32 grow_navigation(u32 control) {
    if(W(control,0xe4)>=37)return 1;
    u32 heap=FN(0x0273d360,u32(*)(u32))(W(0x1018c7ec,0));
    if(!heap)return 0;
    u32 ptr=FN(W(W(heap,12),0x34),u32(*)(u32,u32,u32))(heap,37*4,4);
    if(!ptr)return 0;
    u32 old=W(control,0xe8),count=W(control,0xec);
    if(count>36)count=36;
    for(u32 i=0;i<37;i++)W(ptr,i*4)=i<count?W(old,i*4):0;
    W(control,0xe8)=ptr;W(control,0xe4)=37;
    if(old) {
        u32 owner=FN(0x0273d1e0,u32(*)(u32,u32))(W(0x1018c7ec,0),old);
        if(owner)FN(W(W(owner,12),0x3c),void(*)(u32,u32))(owner,old);
    }
    return 1;
}
void character_setup(u32 page) {
    original_char_setup(page);
    static const u32 ids[37]={0,1,2,3,12,13,4,5,7,16,15,6,
        17,18,19,20,21,14,8,9,10,11,26,27,23,22,24,25,28,29,
        30,34,31,32,33,35,37};
    u32 array=character_button_array(page),control=W(page,0xac);
    if(!W(array,36*4) || !control || !grow_navigation(control))return;
    FN(0x02537680,void(*)(u32))(control);
    for(u32 i=0;i<37;i++) {
        u32 button=W(array,i*4),id=ids[i],state=4;
        if(!button)continue;
        character_available(page,&state,&id);
        B(button,0xf4)=state==5;
        W(button,0x38)|=0x80000000u;
        character_button(button,&id,&state);
        FN(0x0253783c,void(*)(u32,u32))(control,button);
    }
    u32 grid=W(control,0xe0);
    if(grid)W(grid,8)=6;
}

void character_recipe(u32 object,u32 parameters,const u32 *source) {
    if(!source || source[0]!=37) {previous_char_recipe(object,parameters,source);return;}
    u32 local[9];for(u32 i=0;i<9;i++)local[i]=source[i];
    local[0]=28;local[1]=0;
    u32 previous=rob_recipe_scope;rob_recipe_scope=1;
    previous_char_recipe(object,parameters,local);
    rob_recipe_scope=previous;
}
/* Resource finalisation also builds ancillary driver names after the model
 * recipe. Resolve the entire synchronous operation through the donor while
 * retaining the independent identity in the caller's mutable descriptor. */
void character_finalise(u32 object,u32 parameters) {
    if(W(object,0)!=37){original_char_finalise(object,parameters);return;}
    u32 previous=rob_recipe_scope;
    W(object,0)=28;rob_recipe_scope=1;
    original_char_finalise(object,parameters);
    /* Retain an explicit final driver resource path after all native and
     * pre-existing costume/vehicle recipe wrappers have completed. */
    FN(0x02740e1c,void(*)(u32,const char*,...))(object+0x32c,"%s",
        "custom/characters/ROB/driver/ROB.bfres");
#ifdef ROB_PRIVATE_VOICE
    FN(0x02740e1c,void(*)(u32,const char*,...))(object+0xc0c,"%s",
        "audio/driver/SNDG_ROB.bars");
    FN(0x02740e1c,void(*)(u32,const char*,...))(object+0xc58,"%s",
        "audio/driver_menu/SNDG_M_ROB.bars");
#endif
    W(object,0)=37;rob_recipe_scope=previous;
}
static u32 equal(const char *a,const char *b) {
    if(!a || !b)return 0;
    for(u32 i=0;i<64;i++){if(a[i]!=b[i])return 0;if(!a[i])return 1;}
    return 0;
}
void character_prefix(u32 object,const char *prefix,u32 source) {
    if(rob_recipe_scope && equal(prefix,"driver/"))prefix="custom/characters/ROB/driver/";
    if(rob_recipe_scope && equal(prefix,"kart/emblem/"))prefix="custom/characters/ROB/kart/emblem/";
    if(rob_recipe_scope && source && equal(prefix,"kart/body_tex/")) {
        char name[64];u32 text=W(source,0),i=0;
        if(text) {
            for(;i<63 && B(text,i);i++)name[i]=B(text,i);
            name[i]=0;
            if(equal(name,"BodyK_Std_Mtn_Alb") || equal(name,"BodyK_Skl_Mtn_Alb") ||
               equal(name,"BodyB_Std_Mtn_Alb") || equal(name,"BodyV_Atv_Mtn_Alb"))
                prefix="custom/characters/ROB/kart/body_tex/";
        }
    }
    previous_char_prefix(object,prefix,source);
}
