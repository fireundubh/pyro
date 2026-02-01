import logging
import sys

from copy import deepcopy
from typing import Union

from pyro.Comparators import (endswith,
                              startswith)
from pyro.Exceptions import AnonymizationError, PexReadError
from pyro.PapyrusProject import PapyrusProject
from pyro.services.AnonymizationService import AnonymizationService
from pyro.services.CompilationService import (
    CompileData,
    CompileDataCaprica,
    CompilationService,
)
from pyro.services.PackagingService import PackageData, PackagingService
from pyro.services.ZipService import ZippingData, ZipService


class BuildFacade:
    log: logging.Logger = logging.getLogger('pyro')

    ppj: PapyrusProject

    def __init__(self, ppj: PapyrusProject) -> None:
        self.ppj = ppj
        self._anonymization_service = AnonymizationService(ppj)
        self._compilation_service = CompilationService(ppj)
        self._packaging_service = PackagingService(ppj)
        self._zip_service = ZipService(ppj)

        self.scripts_count = len(self.ppj.psc_paths)

        # WARN: if methods are renamed and their respective option names are not, this will break.
        options: dict[str, object] = deepcopy(self.ppj.options.__dict__)

        for key in options:
            if key in ('args', 'input_path', 'anonymize', 'package', 'zip', 'zip_compression'):
                continue
            if startswith(key, ('ignore_', 'no_', 'force_', 'create_', 'resolve_'), ignorecase=True):
                continue
            if endswith(key, '_token', ignorecase=True):
                continue
            setattr(self.ppj.options, key, getattr(self.ppj, f'get_{key}')())

    def _find_modified_scripts(self) -> list[str]:
        """Delegate to AnonymizationService for backward compatibility."""
        try:
            return self._anonymization_service.find_modified_scripts()
        except PexReadError as e:
            BuildFacade.log.error(str(e))
            sys.exit(1)

    @staticmethod
    def _limit_priority() -> None:
        """Delegate to CompilationService for backward compatibility."""
        CompilationService._limit_priority()

    def get_compile_data(self) -> Union[CompileData, CompileDataCaprica]:
        """Get compile data from the compilation service."""
        return self._compilation_service.get_compile_data()

    @property
    def compile_data(self) -> CompileData:
        """Access compile data from the compilation service."""
        return self._compilation_service.compile_data

    @property
    def compile_data_caprica(self) -> CompileDataCaprica:
        """Access Caprica compile data from the compilation service."""
        return self._compilation_service.compile_data_caprica

    @property
    def package_data(self) -> PackageData:
        """Access package data from the packaging service."""
        return self._packaging_service.package_data

    @property
    def zipping_data(self) -> ZippingData:
        """Access zipping data from the zip service."""
        return self._zip_service.zipping_data

    def try_compile(self) -> None:
        """Builds and passes commands to Papyrus Compiler"""
        self._compilation_service.try_compile()

    def try_anonymize(self) -> None:
        """Obfuscates identifying metadata in compiled scripts"""
        try:
            self._anonymization_service.try_anonymize()
        except AnonymizationError as e:
            BuildFacade.log.error(str(e))
            sys.exit(1)

    def try_pack(self) -> None:
        """Generates BSA/BA2 packages for project"""
        self._packaging_service.try_pack()

    def try_zip(self) -> None:
        """Generates ZIP file for project"""
        self._zip_service.try_zip()
