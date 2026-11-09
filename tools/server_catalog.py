"""Export stable custom-course identities and content revisions for Protarium.

This does not assign native NEX course numbers. Cup/slot are display locations;
identity is derived from the custom directory and survives moving a cup.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import cup0

# Native cup order, independent of the Booster donor mapping.
NATIVE = [
('Gu_FirstCircuit','Mario Kart Stadium'),('Gu_WaterPark','Water Park'),('Gu_Cake','Sweet Sweet Canyon'),('Gu_DossunIseki','Thwomp Ruins'),
('Gu_MarioCircuit','Mario Circuit'),('Gu_City','Toad Harbor'),('Gu_HorrorHouse','Twisted Mansion'),('Gu_Expert','Shy Guy Falls'),
('Gu_Airport','Sunshine Airport'),('Gu_Ocean','Dolphin Shoals'),('Gu_Techno','Electrodrome'),('Gu_SnowMountain','Mount Wario'),
('Gu_Cloud','Cloudtop Cruise'),('Gu_Desert','Bone-Dry Dunes'),('Gu_BowserCastle',"Bowser's Castle"),('Gu_RainbowRoad','Rainbow Road'),
('Gwii_MooMooMeadows','Wii Moo Moo Meadows'),('Gagb_MarioCircuit','GBA Mario Circuit'),('Gds_PukupukuBeach','DS Cheep Cheep Beach'),('G64_KinopioHighway','N64 Toad\'s Turnpike'),
('Ggc_DryDryDesert','GCN Dry Dry Desert'),('Gsfc_DonutsPlain3','SNES Donut Plains 3'),('G64_PeachCircuit','N64 Royal Raceway'),('G3ds_DKJungle','3DS DK Jungle'),
('Gds_WarioStadium','DS Wario Stadium'),('Ggc_SherbetLand','GCN Sherbet Land'),('G3ds_MusicPark','3DS Music Park'),('G64_YoshiValley','N64 Yoshi Valley'),
('Gds_TickTockClock','DS Tick-Tock Clock'),('G3ds_PackunSlider','3DS Piranha Plant Slide'),('Gwii_GrumbleVolcano','Wii Grumble Volcano'),('G64_RainbowRoad','N64 Rainbow Road'),
('Dgc_YoshiCircuit','GCN Yoshi Circuit'),('Du_ExciteBike','Excitebike Arena'),('Du_DragonRoad','Dragon Driftway'),('Du_MuteCity','Mute City'),
('Dwii_WariosMine',"Wii Wario's Gold Mine"),('Dsfc_RainbowRoad','SNES Rainbow Road'),('Du_IcePark','Ice Ice Outpost'),('Du_Hyrule','Hyrule Circuit'),
('Dgc_BabyPark','GCN Baby Park'),('Dagb_CheeseLand','GBA Cheese Land'),('Du_Woods','Wild Woods'),('Du_Animal_Summer','Animal Crossing'),
('D3ds_NeoBowserCity','3DS Neo Bowser City'),('Dagb_RibbonRoad','GBA Ribbon Road'),('Du_Metro','Super Bell Subway'),('Du_BigBlue','Big Blue')]


def tree_digest(paths):
    result = hashlib.sha256()
    for prefix, root in paths:
        if not root.is_dir():
            continue
        for path in sorted((p for p in root.rglob('*') if p.is_file()), key=lambda p: p.relative_to(root).as_posix()):
            label = (prefix + '/' + path.relative_to(root).as_posix()).encode('utf-8')
            payload = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1 << 20), b''):
                    payload.update(block)
            result.update(len(label).to_bytes(4, 'big') + label + payload.digest())
    return result.hexdigest()


def export(content, output, header=None, include_native=False):
    content = Path(content).resolve(strict=True)
    tracks = []
    seen = set()
    for cup in cup0.parse((content / 'data.cup0').read_bytes()):
        for slot, track in enumerate(cup.tracks):
            if track.dir == 'Ginvalid':
                continue
            if Path(track.dir).name != track.dir or not re.fullmatch(r'[A-Za-z0-9_-]+', track.dir):
                raise ValueError('Unsafe course directory: ' + track.dir)
            course = content / 'course' / track.dir
            for required in cup0.REQUIRED:
                if not (course / required).is_file():
                    raise FileNotFoundError(course / required)
            identity = 'ct.' + track.dir.lower()
            if identity in seen:
                raise ValueError('Duplicate course identity: ' + identity)
            seen.add(identity)
            revision = tree_digest([('course', course), ('objects', content / 'custom/course_assets' / track.dir)])
            tracks.append(dict(id=identity, revision=revision, name=track.name, directory=track.dir, cup=cup.cup_id, slot=slot, revision_basis='assets'))
    if not tracks:
        raise ValueError('No custom tracks found')
    if include_native:
        for position, (directory, name) in enumerate(NATIVE):
            # Unmodified clients cannot report a new file manifest. Give their
            # boards an explicit version identity, never pretend it is an asset audit.
            revision = hashlib.sha256(('MK8-WiiU-v81/' + directory).encode()).hexdigest()
            tracks.append(dict(id='native.' + directory.lower(), revision=revision,
                               name=name, directory=directory, cup=position // 4, slot=position % 4, revision_basis='game-version'))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(protocol=1, tracks=tracks), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    if header:
        header = Path(header)
        header.parent.mkdir(parents=True, exist_ok=True)
        lines = ['/* Generated from the same catalog used by Protarium. */', '#include "tt_category.h"', 'static const struct CtgpTTTrack ctgp_tt_tracks[]={']
        lines += [' {' + ','.join(json.dumps(row[key], ensure_ascii=True) for key in ('directory', 'id', 'revision')) + '},' for row in tracks]
        lines += ['};', '#define CTGP_TT_TRACK_COUNT (sizeof(ctgp_tt_tracks)/sizeof(ctgp_tt_tracks[0]))', '']
        header.write_text('\n'.join(lines), encoding='utf-8')
    print(f'{len(tracks)} tracks exported to {output}; native wire adapter is separate work')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--content', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--header', type=Path)
    parser.add_argument('--include-native', action='store_true')
    args = parser.parse_args()
    export(args.content, args.output, args.header, args.include_native)
