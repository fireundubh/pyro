import multiprocessing
import os
import time

from pyro.Anonymizer import Anonymizer
from pyro.Logger import Logger
from pyro.PexReader import PexReader
from pyro.PapyrusProject import PapyrusProject
from pyro.TimeElapsed import TimeElapsed


class BuildFacade:
    logger = Logger()

    def __init__(self, ppj: PapyrusProject):
        self.ppj = ppj
        self.pex_reader = PexReader(ppj.project)
        self.psc_paths: tuple = ppj.get_script_paths(True)
        self.pex_paths: tuple = ppj.get_script_paths_compiled()

    def find_modified_scripts(self):
        modified_scripts = []

        for psc_path in self.psc_paths:
            script_name, _ = os.path.splitext(os.path.basename(psc_path))

            # if pex exists, compare time_t in pex header with psc's last modified timestamp
            pex_path: str = [pex_path for pex_path in self.pex_paths if pex_path.endswith('%s.pex' % script_name)][0]
            if not os.path.exists(pex_path):
                continue

            compiled_time: int = self.pex_reader.get_compilation_time(pex_path)

            # if psc is older than the pex
            if os.path.getmtime(psc_path) >= compiled_time:
                modified_scripts.append(pex_path)

        return modified_scripts

    def find_missing_scripts(self) -> list:
        missing_scripts = []

        if len(self.psc_paths) > len(self.pex_paths):
            for psc_path in self.psc_paths:
                script_name = os.path.splitext(os.path.basename(psc_path))[0]
                missing_scripts.extend([pex_path for pex_path in self.pex_paths if not pex_path.endswith('%s.pex' % script_name)])

        return missing_scripts

    def try_anonymize(self):
        modified_scripts: list = self.find_modified_scripts()

        if self.ppj.options.disable_anonymizer:
            self.logger.warn('Anonymization disabled by user.')
        elif not modified_scripts:
            self.logger.error('Cannot anonymize compiled scripts because no source scripts were modified')
        else:
            anonymizer = Anonymizer(self.ppj.project)

            for relative_path in self.pex_paths:
                pex_path = os.path.join(self.ppj.output_path, relative_path)
                self.logger.anon('INFO: Anonymizing: ' + pex_path)
                anonymizer.anonymize_script(pex_path)

    def try_compile(self, time_elapsed: TimeElapsed) -> None:
        commands: tuple = self.ppj._build_commands()

        time_elapsed.start_time = time.time()

        if self.ppj.options.disable_parallel:
            for command in commands:
                print('Executing: %s' % command)
                self.ppj._open_process(command, self.ppj.use_bsarch)
        else:
            multiprocessing.freeze_support()
            p = multiprocessing.Pool(processes=os.cpu_count())
            p.imap(self.ppj._open_process, commands)
            p.close()
            p.join()

        time_elapsed.end_time = time.time()

    def try_pack(self):
        missing_scripts: list = self.find_missing_scripts()

        if not missing_scripts:
            self.ppj.pack_archive()
            return

        self.logger.error('Cannot pack archive because there are missing scripts')
