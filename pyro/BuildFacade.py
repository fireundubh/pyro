import json
import multiprocessing
import os
import time
from copy import deepcopy

from pyro.Anonymizer import Anonymizer
from pyro.JsonLogger import JsonLogger
from pyro.Logger import Logger
from pyro.PackageManager import PackageManager
from pyro.PapyrusProject import PapyrusProject
from pyro.PathHelper import PathHelper
from pyro.PexReader import PexReader
from pyro.ProcessManager import ProcessManager
from pyro.TimeElapsed import TimeElapsed


class BuildFacade(Logger):
    def __init__(self, ppj: PapyrusProject):
        self.ppj = ppj

        # WARN: if methods are renamed and their respective option names are not, this will break.
        options: dict = deepcopy(self.ppj.options.__dict__)

        for key in options:
            if key not in ('args', 'input_path', 'worker_limit', 'anonymize', 'bsarch', 'zip', 'zip_compression') and not key.startswith('no_'):
                setattr(self.ppj.options, key, getattr(self.ppj, 'get_%s' % key)())

        if not self.ppj.options.worker_limit:
            worker_limit: int = 2

            try:
                # noinspection Mypy
                worker_limit = os.cpu_count()  # can be None if indeterminate
            except NotImplementedError:
                pass

            self.ppj.options.worker_limit = worker_limit

        # record project options in log
        if self.ppj.options.log_path:
            self._rotate_logs(5)

            os.makedirs(self.ppj.options.log_path, exist_ok=True)
            log_path = os.path.join(self.ppj.options.log_path, 'pyro-%s.log' % int(time.time()))
            with open(log_path, mode='w', encoding='utf-8') as f:
                options = deepcopy(self.ppj.options.__dict__)
                json.dump(options, f, indent=2)

        self.log_file = JsonLogger(ppj)
        self.log_file.add_record('project_data', {
            'program_path': ppj.program_path,
            'project_path': ppj.project_path,
            'import_paths': ppj.import_paths,
            'psc_paths': ppj.psc_paths,
            'pex_paths': ppj.pex_paths
        })

    def _rotate_logs(self, keep_count: int) -> None:
        if not os.path.isdir(self.ppj.options.log_path):
            return

        # because we're rotating at start, account for new log file
        keep_count = keep_count - 1

        log_files = [f for f in os.listdir(self.ppj.options.log_path) if f.endswith('.log')]
        if not (len(log_files) > keep_count):
            return

        log_paths = [os.path.join(self.ppj.options.log_path, f) for f in log_files]

        logs_to_retain = log_paths[-keep_count:]
        logs_to_remove = [f for f in log_paths if f not in logs_to_retain]

        for f in logs_to_remove:
            try:
                os.remove(f)
            except PermissionError:
                BuildFacade.log.error('Cannot delete log file without permission: %s' % f)

    def _find_modified_scripts(self) -> list:
        pex_paths: list = []

        for psc_path in self.ppj.psc_paths:
            script_name, _ = os.path.splitext(os.path.basename(psc_path))

            # if pex exists, compare time_t in pex header with psc's last modified timestamp
            pex_match: list = [pex_path for pex_path in self.ppj.pex_paths if pex_path.endswith('%s.pex' % script_name)]
            if not pex_match:
                continue

            pex_path: str = pex_match[0]
            if not os.path.isfile(pex_path):
                continue

            try:
                header = PexReader.get_header(pex_path)
            except ValueError:
                BuildFacade.log.warning('Cannot determine compilation time from compiled script due to unknown file magic: "%s"' % pex_path)
                continue

            compiled_time: int = header.compilation_time.value

            # if psc is older than the pex
            if os.path.getmtime(psc_path) >= compiled_time:
                pex_paths.append(pex_path)

        return PathHelper.uniqify(pex_paths)

    def try_compile(self, time_elapsed: TimeElapsed) -> None:
        """Builds and passes commands to Papyrus Compiler"""
        commands: list = self.ppj.build_commands()

        script_count: int = len(self.ppj.psc_paths)

        time_elapsed.start_time = time.time()

        if self.ppj.options.no_parallel:
            for command in commands:
                ProcessManager.run(command)
        elif script_count > 0:
            if script_count == 1:
                ProcessManager.run(commands[0])
            else:
                multiprocessing.freeze_support()
                p = multiprocessing.Pool(processes=min(script_count, self.ppj.options.worker_limit))
                p.imap(ProcessManager.run, commands)
                p.close()
                p.join()

        time_elapsed.end_time = time.time()

    def try_anonymize(self) -> None:
        """Obfuscates identifying metadata in compiled scripts"""
        scripts: list = self._find_modified_scripts()

        if not scripts and not self.ppj.missing_scripts and not self.ppj.options.no_incremental_build:
            BuildFacade.log.error('Cannot anonymize compiled scripts because no source scripts were modified')
        else:
            # these are absolute paths. there's no reason to manipulate them.
            for pex_path in self.ppj.pex_paths:
                if not os.path.isfile(pex_path):
                    BuildFacade.log.warning('Cannot locate file to anonymize: "%s"' % pex_path)
                    continue

                BuildFacade.log.info('Anonymizing "%s"...' % pex_path)
                Anonymizer.anonymize_script(pex_path)

    def try_pack(self) -> None:
        """Generates BSA/BA2 packages for project"""
        package_manager = PackageManager(self.ppj)

        if self.ppj.options.bsarch and os.path.isfile(self.ppj.options.bsarch_path):
            package_manager.create_packages()
        else:
            BuildFacade.log.warning('Cannot create package(s) because packaging was disabled by user')

        if self.ppj.options.zip:
            package_manager.create_zip()
        else:
            BuildFacade.log.warning('Cannot create archive because zipping was disabled by user')
