import json
import multiprocessing
import os
import time

from copy import deepcopy

from pyro.Anonymizer import Anonymizer
from pyro.Logger import Logger
from pyro.PackageManager import PackageManager
from pyro.PapyrusProject import PapyrusProject
from pyro.PexReader import PexReader
from pyro.ProcessManager import ProcessManager
from pyro.TimeElapsed import TimeElapsed


class BuildFacade:
    log = Logger()

    def __init__(self, ppj: PapyrusProject):
        self.ppj = ppj

        # WARN: if methods are renamed and their respective option names are not, this will break.
        for key in self.ppj.options.__dict__:
            if key in ('args', 'input_path', 'game_type', 'game_path', 'registry_path') or key.startswith('no_'):
                continue
            setattr(self.ppj.options, key, getattr(self.ppj, 'get_%s' % key)())

        # record project options in log
        if self.ppj.options.log_path:
            os.makedirs(self.ppj.options.log_path, exist_ok=True)
            log_path = os.path.join(self.ppj.options.log_path, 'pyro-options-%s.log' % int(time.time()))
            with open(log_path, mode='w', encoding='utf-8') as f:
                options: dict = deepcopy(self.ppj.options.__dict__)
                json.dump(options, f, indent=2)

        # noinspection PyAttributeOutsideInit
        self.pex_reader = PexReader(self.ppj.options)

    def _find_modified_scripts(self) -> list:
        scripts = []

        for psc_path in self.ppj.psc_paths:
            script_name, _ = os.path.splitext(os.path.basename(psc_path))

            # if pex exists, compare time_t in pex header with psc's last modified timestamp
            pex_paths: list = [pex_path for pex_path in self.ppj.pex_paths if pex_path.endswith('%s.pex' % script_name)]
            if not pex_paths:
                continue

            pex_path: str = pex_paths[0]
            if not os.path.exists(pex_path):
                continue

            compiled_time: int = self.pex_reader.get_compilation_time(pex_path)

            # if psc is older than the pex
            if os.path.getmtime(psc_path) >= compiled_time:
                scripts.append(pex_path)

        return scripts

    def try_compile(self, time_elapsed: TimeElapsed) -> None:
        """Builds and passes commands to Papyrus Compiler"""
        commands: list = self.ppj.build_commands()

        time_elapsed.start_time = time.time()

        if self.ppj.options.no_parallel:
            for command in commands:
                ProcessManager.run(command, not self.ppj.options.no_bsarch)
        else:
            multiprocessing.freeze_support()
            p = multiprocessing.Pool(processes=os.cpu_count())
            p.imap(ProcessManager.run, commands)
            p.close()
            p.join()

        time_elapsed.end_time = time.time()

    def try_anonymize(self) -> None:
        """Obfuscates identifying metadata in compiled scripts"""
        scripts: list = self._find_modified_scripts()

        if not scripts and not self.ppj.missing_script_names and not self.ppj.options.no_incremental_build:
            self.log.error('Cannot anonymize compiled scripts because no source scripts were modified')
        else:
            anonymizer = Anonymizer(self.ppj.options)

            for pex_path in self.ppj.pex_paths:
                if self.ppj.options.game_type == 'fo4':
                    namespace, file_name = map(lambda x: os.path.basename(x), [os.path.dirname(pex_path), pex_path])
                    target_path = os.path.join(self.ppj.options.output_path, namespace, file_name)
                else:
                    pex_path = os.path.basename(pex_path)
                    target_path = os.path.join(self.ppj.options.output_path, pex_path)

                if not os.path.exists(target_path):
                    self.log.error('Cannot locate file to anonymize: "%s"' % target_path)
                    continue

                self.log.anon('Anonymizing "%s"...' % target_path)
                anonymizer.anonymize_script(target_path)

    def try_pack(self) -> None:
        """Generates ZIP archive for project"""
        package_manager = PackageManager(self.ppj)
        package_manager.create_archive()
