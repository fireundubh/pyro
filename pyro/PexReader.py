import os
from typing import IO


class PexData:
    offset: int
    data: bytes
    value: object


class PexInt(PexData):
    value: int


class PexStr(PexData):
    value: str


class PexHeader:
    size: int = 0

    magic: PexInt = PexInt()
    major_version: PexInt = PexInt()
    minor_version: PexInt = PexInt()
    game_id: PexInt = PexInt()
    compilation_time: PexInt = PexInt()

    script_path_size: PexInt = PexInt()
    script_path: PexStr = PexStr()

    user_name_size: PexInt = PexInt()
    user_name: PexStr = PexStr()

    computer_name_size: PexInt = PexInt()
    computer_name: PexStr = PexStr()

    endianness: str = ''

    def __init__(self, endianness: str = 'little') -> None:
        self.endianness = endianness

    def read(self, f: IO, name: str, length: int) -> None:
        obj = getattr(self, name)
        obj.offset, obj.data = f.tell(), f.read(length)

        if isinstance(obj, PexInt):
            obj.value = int.from_bytes(obj.data, self.endianness, signed=False)
        elif isinstance(obj, PexStr):
            obj.value = obj.data.decode('ascii')


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
                raise ValueError('Cannot determine endianness from file magic')

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
