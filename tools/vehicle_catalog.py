"""Shared additional-part catalog used by tables, labels and native compilation."""
BODIES=[
    dict(key='Speeder8',name='Speeder 8',id=39,donor=7,flag=1,message=0x7000,prefix='custom/vehicles/Speeder8/Blue/kart/body/'),
    dict(key='RedOffroader',name='Red Offroader',id=40,donor=30,flag=4,message=0x7002,prefix='custom/vehicles/RedOffroader/kart/body/'),
    dict(key='Wildfire',name='Wildfire',id=41,donor=7,flag=16,message=0x7003,prefix='custom/vehicles/Wildfire/kart/body/'),
]
TIRES=[
    dict(key='SilverMonster',name='Silver Monster',id=21,donor=12,flag=2,message=0x7001,prefix='custom/vehicles/SilverMonster/kart/tire/'),
    dict(key='SNESTires',name='SNES Tires',id=22,donor=11,flag=8,message=0x7004,prefix='custom/vehicles/SNESTires/kart/tire/'),
]
CHOICES=BODIES+TIRES
def icon(c):return 'timg/ct_KP_'+c['key']+'^q.bflim'
def native_header():
    lines=['/* Generated from vehicle_catalog.py. */','struct VehicleChoice {u32 id,donor,flag,message;const char *prefix,*icon;};']
    for name,choices in [('body',BODIES),('tire',TIRES)]:
        lines += [f'#define VEHICLE_{name.upper()}_COUNT {len(choices)}u',f'static const struct VehicleChoice vehicle_{name}_choices[]={{']
        for c in choices:lines.append('{%du,%du,%du,%du,"%s","%s"},'%(c['id'],c['donor'],c['flag'],c['message'],c['prefix'],icon(c)[5:]))
        lines.append('};')
    return '\n'.join(lines)+'\n'
