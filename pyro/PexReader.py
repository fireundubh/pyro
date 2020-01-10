import binascii
import json
import os

from pyro.PexHeader import PexHeader
from pyro.PexTypes import PexInt, PexStr


class PexReader:
    @staticmethod
    def get_header(path: str) -> PexHeader:
        header = PexHeader()

        with open(path, mode='rb') as f:
            f.seek(0, os.SEEK_SET)

            header.read(f, 'magic', 4)

            if header.magic.value == 0xFA57C0DE:  # Fallout 4
                header.endianness = 'little'
            elif header.magic.value == 0xDEC057FA:  # Skyrim LE/SE
                header.endianness = 'big'
            else:
                raise ValueError(f'Cannot determine endianness from file magic in "{path}"')

            header.read(f, 'major_version', 1)
            header.read(f, 'minor_version', 1)
            header.read(f, 'game_id', 2)
            header.read(f, 'compilation_time', 8)
            header.read(f, 'script_path_size', 2)
            header.read(f, 'script_path', header.script_path_size.value)
            header.read(f, 'user_name_size', 2)
            header.read(f, 'user_name', header.user_name_size.value)
            header.read(f, 'computer_name_size', 2)
            header.read(f, 'computer_name', header.computer_name_size.value)
            header.size = f.tell()

        return header

    @staticmethod
    def dump(file_path: str) -> str:
        header = PexReader.get_header(file_path).__dict__

        for key, value in header.items():
            if not isinstance(value, (PexInt, PexStr)):
                continue

            header[key] = value.__dict__

            for k, v in header[key].items():
                if not isinstance(v, bytes):
                    continue

                bytes2hex = binascii.hexlify(v).decode('ascii').upper()
                header[key][k] = ' '.join(bytes2hex[i:i + 2] for i in range(0, len(bytes2hex), 2))

        return json.dumps(header, indent=4)
