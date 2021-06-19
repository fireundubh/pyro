import logging
import multiprocessing
import os
import sys
import time
from copy import deepcopy
from dataclasses import (dataclass,
                         field)

import psutil

from pyro.Anonymizer import Anonymizer
from pyro.PackageManager import PackageManager
from pyro.PapyrusProject import PapyrusProject
from pyro.PathHelper import PathHelper
from pyro.PexReader import PexReader
from pyro.ProcessManager import ProcessManager
from pyro.Enums.ProcessState import ProcessState
from pyro.TimeElapsed import TimeElapsed

from pyro.Comparators import (endswith,
                              startswith)


@dataclass
class CompileData:
    time: TimeElapsed = field(init=False, default_factory=TimeElapsed)
    scripts_count: int = field(init=False, default_factory=int)
    success_count: int = field(init=False, default_factory=int)
    command_count: int = field(init=False, default_factory=int)

    def __post_init__(self):
        self.time = TimeElapsed()

    @property
    def failed_count(self) -> int:
        return self.command_count - self.success_count

    def to_string(self):
        raw_time, avg_time = ('{0:.3f}s'.format(t)
                              for t in (self.time.value(), self.time.average(self.success_count)))

        return f'Compile time: ' \
               f'{raw_time} ({avg_time}/script) - ' \
               f'{self.success_count} succeeded, ' \
               f'{self.failed_count} failed ' \
               f'({self.scripts_count} scripts)'


@dataclass
class PackageData:
    time: TimeElapsed = field(init=False, default_factory=TimeElapsed)
    file_count: int = field(init=False, default_factory=int)

    def __post_init__(self):
        self.time = TimeElapsed()

    def to_string(self):
        raw_time, avg_time = ('{0:.3f}s'.format(t)
                              for t in (self.time.value(), self.time.average(self.file_count)))

        return f'Package time: ' \
               f'{raw_time} ({avg_time}/file, {self.file_count} files)'


@dataclass
class ZippingData:
    time: TimeElapsed = field(init=False, default_factory=TimeElapsed)
    file_count: int = field(init=False, default_factory=int)

    def __post_init__(self):
        self.time = TimeElapsed()

    def to_string(self):
        raw_time, avg_time = ('{0:.3f}s'.format(t)
                              for t in (self.time.value(), self.time.average(self.file_count)))

        return f'Zipping time: ' \
               f'{raw_time} ({avg_time}/file, {self.file_count} files)'


class BuildFacade:
    log: logging.Logger = logging.getLogger('pyro')

    ppj: PapyrusProject = None

    compile_data: CompileData = CompileData()
    package_data: PackageData = PackageData()
    zipping_data: ZippingData = ZippingData()

    def __init__(self, ppj: PapyrusProject) -> None:
        self.ppj = ppj

        self.scripts_count = len(self.ppj.psc_paths)

        # WARN: if methods are renamed and their respective option names are not, this will break.
        options: dict = deepcopy(self.ppj.options.__dict__)

        for key in options:
            if key in ('args', 'input_path', 'anonymize', 'package', 'zip', 'zip_compression'):
                continue
            if startswith(key, ('ignore_', 'no_', 'force_', 'create_', 'resolve_'), ignorecase=True):
                continue
            if endswith(key, '_token', ignorecase=True):
                continue
            setattr(self.ppj.options, key, getattr(self.ppj, f'get_{key}')())

    def _find_modified_scripts(self) -> list:
        pex_paths: list = []

        for object_name, script_path in self.ppj.psc_paths.items():
            script_name, _ = os.path.splitext(os.path.basename(script_path))

            # if pex exists, compare time_t in pex header with psc's last modified timestamp
            pex_match: list = [pex_path for pex_path in self.ppj.pex_paths
                               if endswith(pex_path, f'{script_name}.pex', ignorecase=True)]
            if not pex_match:
                continue

            pex_path: str = pex_match[0]
            if not os.path.isfile(pex_path):
                continue

            try:
                header = PexReader.get_header(pex_path)
            except ValueError:
                BuildFacade.log.error(f'Cannot determine compilation time due to unknown magic: "{pex_path}"')
                sys.exit(1)

            psc_last_modified: float = os.path.getmtime(script_path)
            pex_last_compiled: float = float(header.compilation_time.value)

            # if psc is older than the pex
            if psc_last_modified < pex_last_compiled:
                pex_paths.append(pex_path)

        return PathHelper.uniqify(pex_paths)

    @staticmethod
    def _limit_priority() -> None:
        process = psutil.Process(os.getpid())
        process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if sys.platform == 'win32' else 19)

    def try_compile(self) -> None:
        """Builds and passes commands to Papyrus Compiler"""
        commands: list = self.ppj.build_commands()

        self.compile_data.command_count = len(commands)

        self.compile_data.time.start_time = time.time()

        if self.ppj.options.no_parallel or self.compile_data.command_count == 1:
            for command in commands:
                if ProcessManager.run_compiler(command) == ProcessState.SUCCESS:
                    self.compile_data.success_count += 1
        elif self.compile_data.command_count > 0:
            multiprocessing.freeze_support()
            worker_limit = min(self.compile_data.command_count, self.ppj.options.worker_limit)
            with multiprocessing.Pool(processes=worker_limit,
                                      initializer=BuildFacade._limit_priority) as pool:
                for state in pool.imap(ProcessManager.run_compiler, commands):
                    if state == ProcessState.SUCCESS:
                        self.compile_data.success_count += 1
                pool.close()
                pool.join()

        self.compile_data.time.end_time = time.time()

    def try_anonymize(self) -> None:
        """Obfuscates identifying metadata in compiled scripts"""
        scripts: list = self._find_modified_scripts()

        if not scripts and not self.ppj.missing_scripts and not self.ppj.options.no_incremental_build:
            BuildFacade.log.error('Cannot anonymize compiled scripts because no source scripts were modified')
        else:
            # these are absolute paths. there's no reason to manipulate them.
            for pex_path in self.ppj.pex_paths:
                if not os.path.isfile(pex_path):
                    BuildFacade.log.error(f'Cannot locate file to anonymize: "{pex_path}"')
                    sys.exit(1)

                Anonymizer.anonymize_script(pex_path)

    def try_pack(self) -> None:
        """Generates BSA/BA2 packages for project"""
        self.package_data.time.start_time = time.time()
        package_manager = PackageManager(self.ppj)
        package_manager.create_packages()
        self.package_data.time.end_time = time.time()
        self.package_data.file_count = package_manager.includes

    def try_zip(self) -> None:
        """Generates ZIP file for project"""
        self.zipping_data.time.start_time = time.time()
        package_manager = PackageManager(self.ppj)
        package_manager.create_zip()
        self.zipping_data.time.end_time = time.time()
        self.zipping_data.file_count = package_manager.includes
