import os
import struct


class PexData:
    offset: int
    data: bytes
    value: object


class PexInt(PexData):
    value: int


class PexStr(PexData):
    value: str


class PexHeader:
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


class PexReader:
    @staticmethod
    def get_header(path: str) -> PexHeader:
        header = PexHeader()

        with open(path, 'rb') as f:
            f.seek(0, os.SEEK_SET)

            header.magic.offset, header.magic.data = f.tell(), f.read(4)
            header.magic.value = int.from_bytes(header.magic.data, 'little', signed=False)
            if header.magic.value == 0xFA57C0DE:
                # Fallout 4
                endianness = 'little'
            elif header.magic.value == 0xDEC057FA:
                # Skyrim LE/SE
                endianness = 'big'
            else:
                raise ValueError("Invalid pex file")

            header.major_version.offset, header.major_version.data = f.tell(), f.read(1)
            header.major_version.value = int.from_bytes(header.major_version.data, endianness, signed=False)

            header.minor_version.offset, header.minor_version.data = f.tell(), f.read(1)
            header.minor_version.value = int.from_bytes(header.minor_version.data, endianness, signed=False)

            header.game_id.offset, header.game_id.data = f.tell(), f.read(2)
            header.game_id.value = int.from_bytes(header.game_id.data, endianness, signed=False)

            header.compilation_time.offset, header.compilation_time.data = f.tell(), f.read(8)
            header.compilation_time.value = int.from_bytes(header.compilation_time.data, endianness, signed=False)

            header.script_path_size.offset, header.script_path_size.data = f.tell(), f.read(2)
            header.script_path_size.value = int.from_bytes(header.script_path_size.data, endianness, signed=False)

            header.script_path.offset, header.script_path.data = f.tell(), f.read(header.script_path_size.value)
            header.script_path.value = header.script_path.data.decode('ascii')

            header.user_name_size.offset, header.user_name_size.data = f.tell(), f.read(2)
            header.user_name_size.value = int.from_bytes(header.user_name_size.data, endianness, signed=False)

            header.user_name.offset, header.user_name.data = f.tell(), f.read(header.user_name_size.value)
            header.user_name.value = header.user_name.data.decode('ascii')

            header.computer_name_size.offset, header.computer_name_size.data = f.tell(), f.read(2)
            header.computer_name_size.value = int.from_bytes(header.computer_name_size.data, endianness, signed=False)

            header.computer_name.offset, header.computer_name.data = f.tell(), f.read(header.computer_name_size.value)
            header.computer_name.value = header.computer_name.data.decode('ascii')
        return header
