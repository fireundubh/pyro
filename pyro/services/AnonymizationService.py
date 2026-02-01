"""
AnonymizationService - Handles obfuscation of identifying metadata in compiled PEX scripts.

Extracted from BuildFacade.try_anonymize() and BuildFacade._find_modified_scripts().
"""
import logging
import os
import random
import string
from typing import TYPE_CHECKING

from pyro.Comparators import endswith
from pyro.Exceptions import AnonymizationError, PexReadError
from pyro.PexHeader import PexHeader
from pyro.PexReader import PexReader

if TYPE_CHECKING:
    from pyro.PapyrusProject import PapyrusProject


class AnonymizationService:
    """Service for anonymizing compiled Papyrus scripts."""

    log: logging.Logger = logging.getLogger('pyro')

    def __init__(self, ppj: 'PapyrusProject') -> None:
        self.ppj = ppj

    @staticmethod
    def _randomize_str(size: int, uppercase: bool = False) -> str:
        """Generate a random ASCII string of the given size."""
        charset = string.ascii_uppercase if uppercase else string.ascii_lowercase
        return ''.join(random.choice(charset) for _ in range(size))

    def find_modified_scripts(self) -> list[str]:
        """
        Find PEX files whose source PSC files have been modified since compilation.

        Returns:
            List of absolute paths to PEX files that need re-anonymization.

        Raises:
            PexReadError: If a PEX file has an unknown magic header.
        """
        pex_paths: list[str] = []

        for object_name, script_path in self.ppj.psc_paths.items():
            script_name, _ = os.path.splitext(os.path.basename(script_path))

            # Find matching PEX file
            pex_match: list[str] = [
                pex_path for pex_path in self.ppj.pex_paths
                if endswith(pex_path, f'{script_name}.pex', ignorecase=True)
            ]

            if not pex_match:
                continue

            pex_path: str = pex_match[0]
            if not os.path.isfile(pex_path):
                continue

            try:
                header = PexReader.get_header(pex_path)
            except ValueError as e:
                raise PexReadError(f'Cannot determine compilation time due to unknown magic: "{pex_path}"') from e

            psc_last_modified: float = os.path.getmtime(script_path)
            pex_last_compiled: float = float(header.compilation_time.value)

            # Include PEX if its source PSC is older (meaning PEX is up-to-date)
            if psc_last_modified < pex_last_compiled:
                pex_paths.append(pex_path)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(pex_paths))

    def anonymize_script(self, path: str) -> None:
        """
        Obfuscate script path, user name, and computer name in a compiled script.

        Args:
            path: Absolute path to the PEX file to anonymize.

        Raises:
            AnonymizationError: If the script cannot be anonymized.
        """
        try:
            header: PexHeader = PexReader.get_header(path)
        except ValueError as e:
            raise AnonymizationError(f'Cannot anonymize script due to unknown file magic: "{path}"') from e

        file_path: str = header.script_path.value
        user_name: str = header.user_name.value
        computer_name: str = header.computer_name.value

        # Check if already anonymized (no file extension in path)
        if '.' not in file_path:
            self.log.warning(f'Cannot anonymize script again: "{path}"')
            return

        if not endswith(file_path, '.psc', ignorecase=True):
            raise AnonymizationError(f'Cannot anonymize script due to invalid file extension: "{path}"')

        if not len(file_path) > 0:
            raise AnonymizationError(f'Cannot anonymize script due to zero-length file path: "{path}"')

        if not len(user_name) > 0:
            raise AnonymizationError(f'Cannot anonymize script due to zero-length user name: "{path}"')

        if not len(computer_name) > 0:
            raise AnonymizationError(f'Cannot anonymize script due to zero-length computer name: "{path}"')

        with open(path, mode='r+b') as f:
            f.seek(header.script_path.offset, os.SEEK_SET)
            f.write(bytes(self._randomize_str(header.script_path_size.value), encoding='ascii'))

            f.seek(header.user_name.offset, os.SEEK_SET)
            f.write(bytes(self._randomize_str(header.user_name_size.value), encoding='ascii'))

            f.seek(header.computer_name.offset, os.SEEK_SET)
            f.write(bytes(self._randomize_str(header.computer_name_size.value, True), encoding='ascii'))

        self.log.info(f'Anonymized "{path}"...')

    def anonymize_all(self, pex_paths: list[str]) -> int:
        """
        Anonymize all provided PEX files.

        Args:
            pex_paths: List of absolute paths to PEX files.

        Returns:
            Number of successfully anonymized scripts.

        Raises:
            AnonymizationError: If a PEX file cannot be located.
        """
        count = 0
        for pex_path in pex_paths:
            if not os.path.isfile(pex_path):
                raise AnonymizationError(f'Cannot locate file to anonymize: "{pex_path}"')

            self.anonymize_script(pex_path)
            count += 1

        return count

    def try_anonymize(self) -> None:
        """
        Anonymize all compiled scripts in the project.

        This is the main entry point, matching the original BuildFacade.try_anonymize() API.

        Raises:
            AnonymizationError: If anonymization fails.
        """
        scripts: list[str] = self.find_modified_scripts()

        if not scripts and not self.ppj.missing_scripts and not self.ppj.options.no_incremental_build:
            self.log.error('Cannot anonymize compiled scripts because no source scripts were modified')
            return

        self.anonymize_all(self.ppj.pex_paths)
