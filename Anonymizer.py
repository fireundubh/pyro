import random
import string
from typing import BinaryIO

from Project import Project


class Anonymizer:
    def __init__(self, project: Project):
        self.project = project

    @staticmethod
    def _randomize_str(length: int, uppercase: bool = False) -> str:
        return ''.join([random.choice(string.ascii_lowercase if not uppercase else string.ascii_uppercase) for _ in range(length)])

    def _get_metadata(self, file_path: str) -> list:
        with open(file_path, mode='rb') as data:
            offset = 17 if not self.project.is_fallout4 else 16
            data.seek(offset)
            file_name = self._read_fixed_length_str(data)
            user_name = self._read_fixed_length_str(data)
            sys_name = self._read_fixed_length_str(data)
            return [file_name, user_name, sys_name]

    def _read_fixed_length_str(self, data: BinaryIO) -> str:
        str_length = int.from_bytes(data.read(1), byteorder='little')
        if str_length <= 0:
            return ''

        # skip null byte
        if self.project.is_fallout4:
            data.read(1)

        str_data = data.read(str_length).decode(encoding='ascii')

        # skip null byte
        if not self.project.is_fallout4:
            data.read(1)

        return str_data

    def anonymize_script(self, file_path: str) -> None:
        file_name, user_name, sys_name = self._get_metadata(file_path)

        if not (len(file_name) > 0 and file_name.endswith('.psc') and len(user_name) > 0 and len(sys_name) > 0):
            return

        def write_random_name(data: BinaryIO, name: str, uppercase: bool = False) -> None:
            result = Anonymizer._randomize_str(len(name), uppercase)
            data.write(bytes(result, encoding='ascii'))

        with open(file_path, mode='r+b') as f:
            f.seek(18 + len(file_name) + 2)
            write_random_name(f, user_name)
            f.read(2)
            write_random_name(f, sys_name, True)
