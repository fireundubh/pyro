import argparse
import logging
import os
import sys

from pyro.BuildFacade import BuildFacade
from pyro.PapyrusProject import PapyrusProject
from pyro.PathHelper import PathHelper
from pyro.ProjectOptions import ProjectOptions
from pyro.TimeElapsed import TimeElapsed


class Application:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname).4s] %(message)s')
    log = logging.getLogger('pyro')

    args: argparse.Namespace = None
    parser: argparse.ArgumentParser = None

    def __init__(self, parser: argparse.ArgumentParser) -> None:
        self.parser = parser

        self.args = self.parser.parse_args()

        if self.args.show_help:
            Application._print_help_and_exit()

        self.args.input_path = self._try_fix_input_path(self.args.input_path)

        if not os.path.isfile(self.args.input_path):
            Application.log.error('Cannot load PPJ at given path because file does not exist: "%s"' % self.args.input_path)
            Application._print_help_and_exit()

    @staticmethod
    def _print_help_and_exit() -> None:
        Application.parser.print_help()
        sys.exit(1)

    @staticmethod
    def _try_fix_input_path(input_path: str) -> str:
        if not input_path:
            Application.log.error('required argument missing: -i INPUT.ppj')
            Application._print_help_and_exit()

        if input_path.casefold().endswith('.psc'):
            Application.log.error('Single script compilation is no longer supported. Use a PPJ file.')
            Application._print_help_and_exit()

        if input_path.casefold().startswith('file:'):
            full_path = PathHelper.url2pathname(input_path)
            input_path = os.path.normpath(full_path)

        if not os.path.isabs(input_path):
            cwd = os.getcwd()
            Application.log.warning('Using working directory: "%s"' % cwd)

            input_path = os.path.join(cwd, input_path)

        Application.log.warning('Using input path: "%s"' % input_path)

        return input_path

    @staticmethod
    def _validate_project(ppj: PapyrusProject) -> None:
        if not ppj.options.game_path:
            Application.log.error('Cannot determine game type from arguments or Papyrus Project')
            Application._print_help_and_exit()

        if not ppj.has_imports_node:
            Application.log.error('Cannot proceed without imports defined in project')
            Application._print_help_and_exit()

        if not ppj.has_scripts_node:
            Application.log.error('Cannot proceed without Scripts defined in project')
            Application._print_help_and_exit()

        if ppj.options.package and not ppj.has_packages_node:
            Application.log.error('Cannot proceed with Package enabled without Packages defined in project')
            Application._print_help_and_exit()

        if ppj.options.zip and not ppj.has_zip_file_node:
            Application.log.error('Cannot proceed with Zip enabled without ZipFile defined in project')
            Application._print_help_and_exit()

    def run(self) -> int:
        options = ProjectOptions(self.args.__dict__)
        ppj = PapyrusProject(options)

        self._validate_project(ppj)

        Application.log.info('Imports found:')
        for path in ppj.import_paths:
            Application.log.info('+ "%s"' % path)

        Application.log.info('Scripts found:')
        for path in ppj.psc_paths:
            Application.log.info('+ "%s"' % path)

        time_elapsed = TimeElapsed()

        build = BuildFacade(ppj)

        # bsarch path is not set until BuildFacade initializes
        if ppj.options.package and not os.path.isfile(ppj.options.bsarch_path):
            Application.log.error('Cannot proceed with Package enabled without valid BSArch path')
            Application._print_help_and_exit()

        success_count, failed_count = build.try_compile(time_elapsed)

        if ppj.options.anonymize:
            if failed_count == 0 or ppj.options.ignore_errors:
                build.try_anonymize()
            else:
                Application.log.warning('Cannot anonymize scripts because %s scripts failed to compile' % failed_count)
        else:
            Application.log.warning('Cannot anonymize scripts because Anonymize is disabled in project')

        if ppj.options.package:
            if failed_count == 0 or ppj.options.ignore_errors:
                build.try_pack()
            else:
                Application.log.warning('Cannot create Packages because %s scripts failed to compile' % failed_count)
        else:
            Application.log.warning('Cannot create Packages because Package is disabled in project')

        if ppj.options.zip:
            if failed_count == 0 or ppj.options.ignore_errors:
                build.try_zip()
            else:
                Application.log.warning('Cannot create ZipFile because %s scripts failed to compile' % failed_count)
        else:
            Application.log.warning('Cannot create ZipFile because Zip is disabled in project')

        if success_count > 0:
            raw_time = time_elapsed.value()
            avg_time = time_elapsed.average(success_count)
            s_raw_time, s_avg_time = ('{0:.3f}s'.format(t) for t in (raw_time, avg_time))

            psc_count = len(ppj.psc_paths)

            Application.log.info('Compilation time: %s (%s/script) - %s succeeded, %s failed (%s scripts)'
                                 % (s_raw_time, s_avg_time, success_count, failed_count, psc_count))
        else:
            Application.log.info('No scripts were compiled.')

        Application.log.info('DONE!')

        return 0
