import argparse
from tempfile import TemporaryDirectory
from pathlib import Path
import hashlib
from typing import Any, NamedTuple, Sequence, BinaryIO

from lbptoolspy import extract_far4, pack_far4, SaveKey
from lbptoolspy import lbpfile2json, json2lbpfile
from lbptoolspy.l0_dec_enc import decrypt_ps4_l0, encrypt_ps4_l0

class LevelIdAndLevelName(NamedTuple):
    level_id: str
    level_name: str


class IncorrectBigFart(Exception):
    ...


class NoLevelsInBigFart(IncorrectBigFart):
    ...


class UnsureWhichBigFartLevelToPick(IncorrectBigFart):
    def __init__(self, message: str, levels_names_and_ids: Sequence[LevelIdAndLevelName]):
        pretty_levels_list = '\n'.join(f'[{x[0]}] {x[1]}' for x in levels_names_and_ids)
        self.levels_names_and_ids = levels_names_and_ids
        self.message_without_level_names_and_ids = message
        super().__init__(f'\n{pretty_levels_list}\n{message}')


class MutipleLevelsInBigfart(UnsureWhichBigFartLevelToPick):
    ...


class IndexChosenInBigFartNotFound(UnsureWhichBigFartLevelToPick):
    ...


class InvalidBinFileForBigFartLevel(IncorrectBigFart):
    ...


class L0BytesAndIsAdventure(NamedTuple):
    lo_bytes: bytes
    is_adventure: bool


def _get_depdency_list(file: BinaryIO) -> list[str]:
    file.seek(3)
    if file.read(1) != b'b':
        return []
    
    file.seek(8)
    file.seek(int.from_bytes(file.read(4),'big'))
    
    sha1s = []
    
    count = int.from_bytes(file.read(4),'big')
    for _ in range(count):
        guid: None | int = None
        found_sha1: str | None = None
        guid_or_hash = file.read(1)[0]
        if guid_or_hash == 2:
            guid = int.from_bytes(file.read(4),'big')
        elif guid_or_hash == 1:
            found_sha1 = file.read(20).hex()
        else:
            raise AssertionError(f'unknwon {guid_or_hash = }')
        
        resource_type = int.from_bytes(file.read(4),'big')
        
        if found_sha1:
            sha1s.append(found_sha1)
    
    return sha1s


def _file_sha1(path: Path) -> str:
    sha1_hex = path.with_suffix('').name
    if len(sha1_hex) == 20*2:
        return sha1_hex
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def get_unused_files(root: Path, bin_path: Path, icon_path: None | Path = None) -> list[Path]:
    """
    Returns every file under `root` that is not needed either directly or
    indirectly through dependencies.
    """

    # Collect every file.
    files = [p for p in root.rglob("*") if p.is_file()]
    files.remove(bin_path)
    if icon_path:
        files.remove(icon_path)

    # print('gathering sha1s of all files')
    sha_to_path = {_file_sha1(path): path for path in files}
    # print('finding trees')

    needed: set[str] = set()

    def mark_needed(sha1: str) -> None:
        if sha1 in needed:
            return

        needed.add(sha1)

        path = sha_to_path.get(sha1)
        if path is None:
            # Dependency not present in this folder.
            return

        with path.open("rb") as f:
            for dep in _get_depdency_list(f):
                mark_needed(dep)

    # Start from every explicitly needed file.
    with open(bin_path,'rb') as f:
        bin_list = _get_depdency_list(f)
    for sha1 in sha_to_path:
        if sha1 in bin_list:
            mark_needed(sha1)

    return [
        path
        for sha1, path in sha_to_path.items()
        if sha1 not in needed
    ]


def bigfart_to_l0(bigfart_path: Path | str, level_id: str | None = None) -> L0BytesAndIsAdventure:
    """Convert a bigfart into an L0 file (decrypted PS4 level backup)
 
    Args:
        bigfart_path (Path | str): input bigfart to convert to L0 file
        level_id (str | None): optional arg for if there is mutiple levels in the bigfart, use this level_id level for the L0 file
    
    Returns:
        L0BytesAndIsAdventure: L0 file bytes to be written to a file, and a bool saying if it is an adventure or not
    """
    if level_id:
        level_id = level_id.strip()
        if level_id.startswith('['):
            level_id = s[1:]
        if level_id.endswith(']'):
            level_id = s[:-1]
    with TemporaryDirectory() as str_tp:
        tp = Path(str_tp)
        bigfart_dump = tp / 'b'
        bigfart_dump.mkdir()
        bigfart_save_key = extract_far4(bigfart_path,bigfart_dump)
        bpr_file = bigfart_dump / f'{bigfart_save_key.root_resource_hash.hex()}.bpr'
        if not bpr_file.is_file():
            bpr_file = bpr_file / bigfart_save_key.root_resource_hash.hex()
        if not bpr_file.is_file():
            raise AssertionError()
        bigfart_json = lbpfile2json(bpr_file)
        if not bigfart_json['resource']['myMoonSlots']:
            raise NoLevelsInBigFart('no levels found')
        # myMoonSlots is a list really, but toolkit has it as a dict with the level id as key
        levels_list = list(bigfart_json['resource']['myMoonSlots'].values())
        def long_lambda(x: Any) -> str:
            if not x['root']:
                try:
                    x['adventure']
                except Exception:
                    return ''
                else:
                    if isinstance(x['adventure']['value'],str):
                        return x['adventure']['value']
                    else:
                        return ''
            else:
                try:
                    x['root']
                except Exception:
                    return ''
                else:
                    if isinstance(x['root']['value'],str):
                        return x['root']['value']
                    else:
                        return ''

        levels_list.sort(key = long_lambda)
        levels_list.sort(key = lambda x: x['name'])
        if (len(levels_list) > 1) and (not level_id):
            raise MutipleLevelsInBigfart('mutiple levels found, please provide a `level_id` for one of the following levels',[LevelIdAndLevelName(x['id'],x['name']) for x in levels_list])
        if level_id:
            try:
                level = bigfart_json['resource']['myMoonSlots'][level_id]
            except KeyError:
                raise IndexChosenInBigFartNotFound(f'{level_id} is not here, please give an id for one of the following levels',[LevelIdAndLevelName(x['id'],x['name']) for x in levels_list])
        else:
            level, = levels_list
        is_adventure = None
        if not level['root']:
            try:
                level['adventure']
            except Exception:
                is_adventure = None
            else:
                if isinstance(level['adventure']['value'],str):
                    root_resource = level['adventure']['value']
                    is_adventure = True
                else:
                    is_adventure = None
        else:
            try:
                level['root']
            except Exception:
                is_adventure = None
            if isinstance(level['root']['value'],str):
                is_adventure = False
                root_resource = level['root']['value']
            else:
                is_adventure = None
        if is_adventure is None:
            InvalidBinFileForBigFartLevel(f'{level_index = } has a null root resource, this means its either a guid level or is just an empty level')
        
        if is_adventure:
            root_resource_ext = '.adc'
        else:
            root_resource_ext = '.bin'
        root_resource_path = bigfart_dump / f'{root_resource}{root_resource_ext}'
        if not root_resource_path.is_file():
            root_resource_path = bigfart_dump / f'{root_resource}'
        if not root_resource_path.is_file():
            raise AssertionError()
        icon_hash = None
        icon_path = None
        try:
            if isinstance(level['icon']['value'],str):
                icon_hash = level['icon']['value']
        except Exception:
            pass
        if icon_hash:
            icon_path = bigfart_dump / f'{icon_hash}.tex'
            if not icon_path.is_file():
                icon_path = bigfart_dump / icon_hash
            if not icon_path.is_file():
                raise AssertionError
        unused_files = get_unused_files(bigfart_dump,root_resource_path,icon_path)
        for file in unused_files:
            file.unlink()
        l0_json = {'revision': 35128313, 'type': 'SLOT_LIST', 'resource': {'slots': [], 'fromProductionBuild': True}}
        l0_save_key = SaveKey.from_string('f9031802000000001f4f991b00000000000000000000000000000000000000000000000000000000000000000000000000000000000000001d000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000')
        l0_id = 'FAKE:0'
        level['id']
        level['id'] = l0_id
        l0_json['resource']['slots'].append(level)

        slt_file = bigfart_dump / f'{bigfart_save_key.root_resource_hash.hex()}.slt'
        dec_l0 = tp / 'l'
        pack_far4(bigfart_dump,dec_l0,l0_save_key,hashlib.sha1(json2lbpfile(l0_json,slt_file)).digest())
        result = encrypt_ps4_l0(dec_l0.read_bytes())
        LBP3_PS4_L0_FILE_MAX_SIZE = 0x2_000_000
        if len(result) > LBP3_PS4_L0_FILE_MAX_SIZE:
            raise Exception(f'The L0 file is too big ({len(result):,} bytes), the max lbp3 ps4 level backup can only be {(LBP3_PS4_L0_FILE_MAX_SIZE):,} bytes')
        return L0BytesAndIsAdventure(result,is_adventure)


def l0_to_bigfart(l0_bytes: bytes, bigfart_path: Path | str) -> None:
    """Convert a L0 (decrypted PS4 level backup) into a bigfart

    Args:
        l0_bytes (bytes): entire L0 bytes contents
        bigfart_path (Path): Path to the output bigfart
    """
    with TemporaryDirectory() as str_tp:
        tp = Path(str_tp)
        
        dec_l0 = tp / 'l'
        dec_l0_dump = tp / 'd'
        dec_l0_dump.mkdir()
        
        dec_l0.write_bytes(decrypt_ps4_l0(l0_bytes))
        l0_save_key = extract_far4(dec_l0,dec_l0_dump)
        slt_file = dec_l0_dump / f'{l0_save_key.root_resource_hash.hex()}.slt'
        if not slt_file.is_file():
            slt_file = dec_l0_dump / l0_save_key.root_resource_hash.hex()
        if not slt_file.is_file():
            raise AssertionError()
        l0_slot = lbpfile2json(slt_file)['resource']['slots'][0]
        new_bigfart_id = 'USER_CREATED_STORED_LOCAL:32'
        try:
            l0_slot['adventure']['value']
        except Exception:
            pass
        else:
            if l0_slot['adventure']['value']:
                new_bigfart_id = 'ADVENTURE_PLANET_LOCAL:82'
        lbp3_ps4_128_bigfart_json_template = {'revision': 35128313, 'type': 'BIG_PROFILE', 'resource': {'inventory': [], 'vitaCrossDependencyHashes': [], 'creatorDataLabels': [], 'stringTable': {'unsorted': False, 'sortEnabled': True, 'rawIndexToSortedIndex': [1, 0], 'stringList': [{'lamsKeyID': 0, 'string': '', 'index': 1}, {'lamsKeyID': -871487226, 'string': 'My Objects', 'index': 0}]}, 'fromProductionBuild': True, 'myMoonSlots': {new_bigfart_id: 6}}}
        l0_slot['id'] = new_bigfart_id
        lbp3_ps4_128_bigfart_json_template['resource']['myMoonSlots'][new_bigfart_id] = l0_slot
        slt_file.unlink()
        new_bpr_sha1 = hashlib.sha1(json2lbpfile(lbp3_ps4_128_bigfart_json_template,dec_l0_dump / f'{l0_save_key.root_resource_hash.hex()}.bpr')).digest()
        bigfart_template_save_key = SaveKey.from_string('f903180200000000c21bb71e00000000000000000000000000000000000000000000000000000000000000000000000000000000000000001c000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000') 
        pack_far4(dec_l0_dump,bigfart_path,bigfart_template_save_key,new_bpr_sha1)


def main() -> None:
    """
    argparse ai gen
    """
    parser = argparse.ArgumentParser(
        description="Convert between bigfart files and L0 (PS4 decrypted level backups)."
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        help="Conversion direction",
    )

    # bigfart -> L0
    to_l0_parser = subparsers.add_parser(
        "to-l0",
        help="Convert a bigfart into an L0 file",
    )
    to_l0_parser.add_argument(
        "input",
        type=Path,
        help="Input bigfart file",
    )
    to_l0_parser.add_argument(
        "output",
        type=Path,
        help="Output L0 file",
    )
    to_l0_parser.add_argument(
        "--level-id",
        type=str,
        default=None,
        help="Level ID to select if the bigfart contains multiple levels",
    )

    # L0 -> bigfart
    to_bigfart_parser = subparsers.add_parser(
        "to-bigfart",
        help="Convert an L0 file into a bigfart",
    )
    to_bigfart_parser.add_argument(
        "input",
        type=Path,
        help="Input L0 file",
    )
    to_bigfart_parser.add_argument(
        "output",
        type=Path,
        help="Output bigfart file",
    )

    args = parser.parse_args()

    if not args.input.is_file():
        raise argparse.ArgumentTypeError(f"Input file does not exist: {args.input}")
    if args.output.exists():
        raise argparse.ArgumentTypeError(f"Output file already exists: {args.output}")

    if args.command == "to-l0":
        result = bigfart_to_l0(args.input, args.level_id)
        args.output.write_bytes(result.lo_bytes)

        print(f"Saved L0 file to {args.output}")
        print(f"Is adventure: {result.is_adventure}")

    elif args.command == "to-bigfart":
        l0_bytes = args.input.read_bytes()
        l0_to_bigfart(l0_bytes, args.output)

        print(f"Saved bigfart file to {args.output}")


if __name__ == "__main__":
    main()
