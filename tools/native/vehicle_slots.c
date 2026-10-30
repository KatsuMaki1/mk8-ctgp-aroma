/* Experimental additional body/tire IDs. Included only by vehicle_patch.py. */
#include "vehicle_catalog.h"
static const struct VehicleChoice *vehicle_choice(u32 kind,u32 id) {
    const struct VehicleChoice *items=kind==0?vehicle_body_choices:vehicle_tire_choices;
    u32 count=kind==0?VEHICLE_BODY_COUNT:VEHICLE_TIRE_COUNT;
    for(u32 i=0;i<count;i++)if(items[i].id==id)return items+i;
    return 0;
}
static u32 vehicle_donor(u32 kind,u32 id) {
    const struct VehicleChoice *c=vehicle_choice(kind,id);return c?c->donor:id;
}
static u32 vehicle_scope(u32 kind,u32 id,u32 flags) {
    const struct VehicleChoice *items=kind==0?vehicle_body_choices:vehicle_tire_choices;
    u32 count=kind==0?VEHICLE_BODY_COUNT:VEHICLE_TIRE_COUNT;
    for(u32 i=0;i<count;i++)if(items[i].id==id || (flags&items[i].flag))return i+1;
    return 0;
}
extern void original_vehicle_setup(u32, const u32 *, u32);
extern void original_vehicle_body(u32, u32);
extern void original_vehicle_tire(u32, u32);
extern void original_vehicle_names(u32);
extern void original_vehicle_recipe(u32, u32, const u32 *);
extern void original_vehicle_prefix(u32, const char *, u32);
extern u32 original_vehicle_icon(u32, u32, u32, u32, u32);
extern u32 original_vehicle_type(u32,const u32 *);
extern u32 original_vehicle_config(u32,u32,const u32 *);
extern u32 original_vehicle_effects(u32,u32,u32,const u32 *);
extern u32 original_vehicle_body_name(u32,const u32 *);

static u32 vehicle_body_scope, vehicle_tire_scope;
static u32 vehicle_recipes[64][2], vehicle_next;
static volatile u32 vehicle_controls[4][2];
__attribute__((used)) volatile u32 vehicle_audio_seen;
static u32 vehicle_flags(u32 object) {
    for(u32 i=0;i<64;i++) if(vehicle_recipes[i][0]==object) return vehicle_recipes[i][1];
    return 0;
}
static void vehicle_remember(u32 object,u32 flags) {
    for(u32 i=0;i<64;i++) if(vehicle_recipes[i][0]==object) {vehicle_recipes[i][1]=flags;return;}
    if(!flags) return;
    u32 i=vehicle_next++%64;vehicle_recipes[i][0]=object;vehicle_recipes[i][1]=flags;
}
u32 vehicle_config_impl(u32 object,u32 parameters,const u32 *source) {
    if(!parameters || !source) return original_vehicle_config(object,parameters,source);
    u32 local[7];for(u32 i=0;i<7;i++)local[i]=source[i];
    const struct VehicleChoice *body=vehicle_choice(0,local[0]),*tire=vehicle_choice(1,local[1]);
    u32 flags=(body?body->flag:0)|(tire?tire->flag:0);
    local[0]=vehicle_donor(0,local[0]);local[1]=vehicle_donor(1,local[1]);
    u32 result=original_vehicle_config(object,parameters,local);
    vehicle_remember(object,flags);
    return result;
}

static u32 vehicle_alloc(u32 bytes) {
    u32 heap = FN(0x0273d360, u32 (*)(u32))(W(0x1018c7ec,0));
    if (!heap) return 0;
    return FN(W(W(heap,0x0c),0x34), u32 (*)(u32,u32,u32))(heap,bytes,4);
}
static void vehicle_free(u32 ptr) {
    u32 heap = FN(0x0273d360, u32 (*)(u32))(W(0x1018c7ec,0));
    if (heap && ptr) FN(W(W(heap,0x0c),0x3c), void (*)(u32,u32))(heap,ptr);
}
static u32 vehicle_grow(u32 old, u32 count, u32 stride,u32 extra) {
    u32 ptr = vehicle_alloc((count+extra)*stride);
    if (!ptr) return 0;
    for (u32 i=0;i<count*stride;i++) B(ptr,i)=B(old,i);
    for (u32 i=count*stride;i<(count+extra)*stride;i++) B(ptr,i)=0;
    return ptr;
}
void costume_vehicle_setup(u32 control,const u32 *kind,u32 single) {
    original_vehicle_setup(control,kind,single);
    if (*kind>1) return;
    u32 width=W(control,0x5c),count=W(control,0x60),old=W(control,0x64);
    if (width!=1 || !old || count!=(*kind==0?40u:22u)) return;
    u32 extra=*kind==0?VEHICLE_BODY_COUNT:VEHICLE_TIRE_COUNT;
    u32 ptr=vehicle_grow(old,count,16,extra);
    if (!ptr) return;
    W(ptr+count*16,0)=0xffffffffu;
    W(control,0x64)=ptr;W(control,0x60)=count+extra;
    vehicle_free(old);
}
static void vehicle_append(u32 control,u32 id) {
    if (W(control,0x5c)!=1 || W(control,0x6a8)>=W(control,0x60)) return;
    u32 entries=W(control,0x64),count=W(control,0x6a8);
    for(u32 i=0;i<count;i++) if(W(entries+i*16,0)==id) return;
    FN(0x025a4ed8,void (*)(u32,u32,u32,u32))(control,id,0,0);
    W(control,0x6c)=W(control,0x6a8);
}
void costume_vehicle_body(u32 control,u32 unlock) {
    original_vehicle_body(control,unlock);
    for(u32 i=0;i<VEHICLE_BODY_COUNT;i++)vehicle_append(control,vehicle_body_choices[i].id);
    u32 player=W(control,0x1a0);if(player<4)vehicle_controls[player][0]=control;
}
void costume_vehicle_tire(u32 control,u32 unlock) {
    original_vehicle_tire(control,unlock);
    for(u32 i=0;i<VEHICLE_TIRE_COUNT;i++)vehicle_append(control,vehicle_tire_choices[i].id);
    u32 player=W(control,0x1a0);if(player<4)vehicle_controls[player][1]=control;
}
static void vehicle_alias_vector(u32 object,u32 count_offset,u32 ptr_offset,u32 expected,u32 kind,u32 labels) {
    u32 count=W(object,count_offset),old=W(object,ptr_offset);
    if(count!=expected || !old) return;
    const struct VehicleChoice *items=kind==0?vehicle_body_choices:vehicle_tire_choices;
    u32 extra=kind==0?VEHICLE_BODY_COUNT:VEHICLE_TIRE_COUNT;
    u32 ptr=vehicle_grow(old,count,4,extra);
    if(!ptr) return;
    for(u32 i=0;i<extra;i++)W(ptr,(count+i)*4)=labels?items[i].message:W(old,(items[i].donor+1)*4);
    W(object,ptr_offset)=ptr;W(object,count_offset)=count+extra;
    vehicle_free(old);
}
void costume_vehicle_names(u32 object) {
    original_vehicle_names(object);
    vehicle_alias_vector(object,0x44,0x48,40,0,0);
    vehicle_alias_vector(object,0x5c,0x60,40,0,1);
    vehicle_alias_vector(object,0x4c,0x50,22,1,0);
    vehicle_alias_vector(object,0x64,0x68,22,1,1);
}
u32 costume_vehicle_icon(u32 object,u32 kind,u32 id,u32 driver,u32 color) {
    const struct VehicleChoice *choice=kind<2?vehicle_choice(kind,id):0;
    const char *name=choice?choice->icon:0;
    if(name) {
        u32 heap=heap_at(4),resource=heap?W(heap,4):0;
        if(resource) {
            struct NativeString path={name,0x100d25d0};
            u32 texture=FN(0x0253d47c,u32 (*)(u32,const struct NativeString *))(resource,&path);
            if(texture) return texture;
        }
    }
    if(choice)id=choice->donor;
    return original_vehicle_icon(object,kind,id,driver,color);
}
void costume_vehicle_recipe(u32 object,u32 parameters,const u32 *recipe) {
    u32 local[9];for(u32 i=0;i<9;i++) local[i]=recipe[i];
    u32 previous_body=vehicle_body_scope,previous_tire=vehicle_tire_scope;
    u32 flags=vehicle_flags((u32)(__UINTPTR_TYPE__)recipe);
    vehicle_body_scope=vehicle_scope(0,local[3],flags);vehicle_tire_scope=vehicle_scope(1,local[6],flags);
    local[3]=vehicle_donor(0,local[3]);local[6]=vehicle_donor(1,local[6]);
    original_vehicle_recipe(object,parameters,local);
    vehicle_body_scope=previous_body;vehicle_tire_scope=previous_tire;
}
static u32 vehicle_equal(const char *a,const char *b) {
    if(!a || !b) return 0;
    for(u32 i=0;i<128;i++) {if(a[i]!=b[i])return 0;if(!a[i])return 1;}
    return 0;
}
void costume_vehicle_prefix(u32 object,const char *prefix,u32 source) {
    if(vehicle_body_scope && vehicle_equal(prefix,"kart/body/"))
        prefix=vehicle_body_choices[vehicle_body_scope-1].prefix;
    if(vehicle_tire_scope && vehicle_equal(prefix,"kart/tire/"))
        prefix=vehicle_tire_choices[vehicle_tire_scope-1].prefix;
    original_vehicle_prefix(object,prefix,source);
}

u32 costume_vehicle_type(u32 output,const u32 *body) {
    if(body) {u32 donor=vehicle_donor(0,*body);return original_vehicle_type(output,&donor);}
    return original_vehicle_type(output,body);
}

/* Particle construction names both body and tire through fixed native enums.
 * Its two-word descriptor is consumed synchronously; retain the selected IDs
 * elsewhere while resolving the donor's drift/smoke/anti-gravity emitters. */
u32 costume_vehicle_effects(u32 object,u32 unit,u32 model,const u32 *parts) {
    if(!parts) return original_vehicle_effects(object,unit,model,parts);
    u32 local[2]={vehicle_donor(0,parts[0]),vehicle_donor(1,parts[1])};
    return original_vehicle_effects(object,unit,model,local);
}

u32 costume_vehicle_body_name(u32 object,const u32 *body) {
    if(body) {u32 donor=vehicle_donor(0,*body);return original_vehicle_body_name(object,&donor);}
    return original_vehicle_body_name(object,body);
}
