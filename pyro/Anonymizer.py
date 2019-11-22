import os
import random
import string

from pyro.Logger import Logger
from pyro.PexReader import PexReader


class Anonymizer(Logger):
    @staticmethod
    def _randomize_str(size: int, uppercase: bool = False) -> str:
        return ''.join([random.choice(string.ascii_lowercase if not uppercase else string.ascii_uppercase) for _ in range(size)])

    @staticmethod
    def anonymize_script(path: str) -> None:
        try:
            header = PexReader.get_header(path)
        except ValueError:
            Anonymizer.log.error('Cannot anonymize compiled script due to unknown file magic: "%s"' % path)
            return

        file_path: str = header.script_path.value
        user_name: str = header.user_name.value
        computer_name: str = header.computer_name.value

        if not len(file_path) > 0 and file_path.endswith('.psc') and len(user_name) > 0 and len(computer_name) > 0:
            return

        with open(path, mode='r+b') as f:
            f.seek(header.user_name.offset, os.SEEK_SET)
            f.write(bytes(Anonymizer._randomize_str(header.user_name_size.value), encoding='ascii'))

            f.seek(header.computer_name.offset, os.SEEK_SET)
            f.write(bytes(Anonymizer._randomize_str(header.computer_name_size.value, True), encoding='ascii'))
