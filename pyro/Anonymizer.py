import os
import random
import string

from pyro.Logger import Logger
from pyro.PexReader import PexReader


class Anonymizer(Logger):
    @staticmethod
    def _randomize_str(size: int, uppercase: bool = False) -> str:
        charset = string.ascii_uppercase if uppercase else string.ascii_lowercase
        return ''.join([random.choice(charset) for _ in range(size)])

    @staticmethod
    def anonymize_script(path: str) -> None:
        try:
            header = PexReader.get_header(path)
        except ValueError:
            Anonymizer.log.error('Cannot anonymize script due to unknown file magic: "%s"' % path)
            return

        file_path: str = header.script_path.value
        user_name: str = header.user_name.value
        computer_name: str = header.computer_name.value

        if not file_path.casefold().endswith('.psc'):
            Anonymizer.log.warning('Cannot anonymize script due to invalid file extension: "%s"' % path)
            return

        if not len(file_path) > 0:
            Anonymizer.log.warning('Cannot anonymize script due to zero-length file path: "%s"' % path)
            return

        if not len(user_name) > 0:
            Anonymizer.log.warning('Cannot anonymize script due to zero-length user name: "%s"' % path)
            return

        if not len(computer_name) > 0:
            Anonymizer.log.warning('Cannot anonymize script due to zero-length computer name: "%s"' % path)
            return

        with open(path, mode='r+b') as f:
            f.seek(header.script_path.offset, os.SEEK_SET)
            f.write(bytes(Anonymizer._randomize_str(header.script_path_size.value), encoding='ascii'))

            f.seek(header.user_name.offset, os.SEEK_SET)
            f.write(bytes(Anonymizer._randomize_str(header.user_name_size.value), encoding='ascii'))

            f.seek(header.computer_name.offset, os.SEEK_SET)
            f.write(bytes(Anonymizer._randomize_str(header.computer_name_size.value, True), encoding='ascii'))

            Anonymizer.log.info('Anonymized "%s"...' % path)
