import logging
import os
import random
import string
import sys

from pyro.PexHeader import PexHeader
from pyro.PexReader import PexReader

from pyro.Comparators import endswith


class Anonymizer:
    log: logging.Logger = logging.getLogger('pyro')

    @staticmethod
    def _randomize_str(size: int, uppercase: bool = False) -> str:
        charset = string.ascii_uppercase if uppercase else string.ascii_lowercase
        return ''.join(random.choice(charset) for _ in range(size))

    @staticmethod
    def anonymize_script(path: str) -> None:
        """
        Obfuscates script path, user name, and computer name in compiled script
        """
        try:
            header: PexHeader = PexReader.get_header(path)
        except ValueError:
            Anonymizer.log.error(f'Cannot anonymize script due to unknown file magic: "{path}"')
            sys.exit(1)

        file_path: str = header.script_path.value
        user_name: str = header.user_name.value
        computer_name: str = header.computer_name.value

        if '.' not in file_path:
            Anonymizer.log.warning(f'Cannot anonymize script again: "{path}"')
            return

        if not endswith(file_path, '.psc', ignorecase=True):
            Anonymizer.log.error(f'Cannot anonymize script due to invalid file extension: "{path}"')
            sys.exit(1)

        if not len(file_path) > 0:
            Anonymizer.log.error(f'Cannot anonymize script due to zero-length file path: "{path}"')
            sys.exit(1)

        if not len(user_name) > 0:
            Anonymizer.log.error(f'Cannot anonymize script due to zero-length user name: "{path}"')
            sys.exit(1)

        if not len(computer_name) > 0:
            Anonymizer.log.error(f'Cannot anonymize script due to zero-length computer name: "{path}"')
            sys.exit(1)

        with open(path, mode='r+b') as f:
            f.seek(header.script_path.offset, os.SEEK_SET)
            f.write(bytes(Anonymizer._randomize_str(header.script_path_size.value), encoding='ascii'))

            f.seek(header.user_name.offset, os.SEEK_SET)
            f.write(bytes(Anonymizer._randomize_str(header.user_name_size.value), encoding='ascii'))

            f.seek(header.computer_name.offset, os.SEEK_SET)
            f.write(bytes(Anonymizer._randomize_str(header.computer_name_size.value, True), encoding='ascii'))

            Anonymizer.log.info(f'Anonymized "{path}"...')
