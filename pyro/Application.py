import argparse
import logging
import os
import sys

from pyro.Enums.Event import (BuildEvent,
                              ImportEvent,
                              CompileEvent,
                              AnonymizeEvent,
                              PackageEvent,
                              ZipEvent)
from pyro.BuildFacade import BuildFacade
from pyro.Comparators import startswith
from pyro.PapyrusProject import PapyrusProject
from pyro.PathUtils import url_to_path
from pyro.PexReader import PexReader
from pyro.ProjectOptions import ProjectOptions


class Application:
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s [%(levelname).4s] %(message)s')
    log = logging.getLogger('pyro')

    project: PapyrusProject
    build_facade: BuildFacade

    def __init__(self, project: PapyrusProject, build_facade: BuildFacade) -> None:
        self.project = project
        self.build_facade = build_facade

    @staticmethod
    def _try_fix_input_path(input_path: str) -> str:
        if not input_path:
            Application.log.error('required argument missing: -i INPUT.ppj')
            sys.exit(1)

        if startswith(input_path, 'file:', ignorecase=True):
            input_path = str(url_to_path(input_path))

        if not os.path.isabs(input_path):
            cwd = os.getcwd()
            Application.log.info(f'Using working directory: "{cwd}"')

            input_path = os.path.join(cwd, input_path)

        Application.log.info(f'Using input path: "{input_path}"')

        return input_path

    @staticmethod
    def _validate_project_file(ppj: PapyrusProject) -> None:
        if ppj.imports_node is None and \
                (ppj.scripts_node is not None or ppj.folders_node is not None):
            Application.log.error('Cannot proceed without imports defined in project')
            sys.exit(1)

        if ppj.options.package and ppj.packages_node is None:
            Application.log.error('Cannot proceed with Package enabled without Packages defined in project')
            sys.exit(1)

        if ppj.options.zip and ppj.zip_files_node is None:
            Application.log.error('Cannot proceed with Zip enabled without ZipFile defined in project')
            sys.exit(1)

    @staticmethod
    def _validate_project_paths(ppj: PapyrusProject) -> None:
        compiler_path = ppj.get_compiler_path()
        if not compiler_path or not os.path.isfile(compiler_path):
            Application.log.error('Cannot proceed without compiler path')
            sys.exit(1)

        flags_path = ppj.get_flags_path()
        if not flags_path:
            Application.log.error('Cannot proceed without flags path')
            sys.exit(1)

        if not ppj.options.game_type:
            Application.log.error('Cannot determine game type from arguments or Papyrus Project')
            sys.exit(1)

        if not os.path.isabs(flags_path) and \
                not any([os.path.isfile(os.path.join(import_path, flags_path)) for import_path in ppj.import_paths]):
            Application.log.error('Cannot proceed without flags file in any import folder')
            sys.exit(1)

    def run(self) -> int:
        """
        Executes the build pipeline using injected dependencies.
        """
        ppj = self.project
        build = self.build_facade

        if ppj.use_pre_build_event:
            ppj.try_run_event(BuildEvent.PRE)

        if build.scripts_count > 0:
            if ppj.use_pre_compile_event:
                ppj.try_run_event(CompileEvent.PRE)

            build.try_compile()

            if ppj.use_post_compile_event:
                ppj.try_run_event(CompileEvent.POST)

            if ppj.options.anonymize:
                if build.get_compile_data().failed_count == 0 or ppj.options.ignore_errors:
                    if ppj.use_pre_anonymize_event:
                        ppj.try_run_event(AnonymizeEvent.PRE)

                    build.try_anonymize()

                    if ppj.use_post_anonymize_event:
                        ppj.try_run_event(AnonymizeEvent.POST)
                else:
                    Application.log.error(f'Cannot anonymize scripts because {build.get_compile_data().failed_count} scripts failed to compile')
                    sys.exit(build.get_compile_data().failed_count)
            else:
                Application.log.info('Cannot anonymize scripts because Anonymize is disabled in project')

        if ppj.options.package:
            if build.get_compile_data().failed_count == 0 or ppj.options.ignore_errors:
                if ppj.use_pre_package_event:
                    ppj.try_run_event(PackageEvent.PRE)

                build.try_pack()

                if ppj.use_post_package_event:
                    ppj.try_run_event(PackageEvent.POST)
            else:
                Application.log.error(f'Cannot create Packages because {build.get_compile_data().failed_count} scripts failed to compile')
                sys.exit(build.get_compile_data().failed_count)
        elif ppj.packages_node is not None:
            Application.log.info('Cannot create Packages because Package is disabled in project')

        if ppj.options.zip:
            if build.get_compile_data().failed_count == 0 or ppj.options.ignore_errors:
                if ppj.use_pre_zip_event:
                    ppj.try_run_event(ZipEvent.PRE)

                build.try_zip()

                if ppj.use_post_zip_event:
                    ppj.try_run_event(ZipEvent.POST)
            else:
                Application.log.error(f'Cannot create ZipFile because {build.get_compile_data().failed_count} scripts failed to compile')
                sys.exit(build.get_compile_data().failed_count)
        elif ppj.zip_files_node is not None:
            Application.log.info('Cannot create ZipFile because Zip is disabled in project')

        if build.scripts_count > 0:
            Application.log.info(build.get_compile_data().to_string() if build.get_compile_data().success_count > 0 else 'No scripts were compiled.')

        if ppj.packages_node is not None:
            Application.log.info(build.package_data.to_string() if build.package_data.file_count > 0 else 'No files were packaged.')

        if ppj.zip_files_node is not None:
            Application.log.info(build.zipping_data.to_string() if build.zipping_data.file_count > 0 else 'No files were zipped.')

        Application.log.info('DONE!')

        if ppj.use_post_build_event and build.get_compile_data().failed_count == 0:
            ppj.try_run_event(BuildEvent.POST)

        return build.get_compile_data().failed_count


def create_application(parser: argparse.ArgumentParser) -> Application:
    """
    Factory function for creating an Application instance in production use.

    This function handles argument parsing, logging setup, project initialization,
    and validation before constructing the Application with its dependencies.

    :param parser: Configured argument parser
    :return: Initialized Application instance ready to run
    """
    # Parse arguments
    args = parser.parse_args()

    if args.show_help:
        parser.print_help()
        sys.exit(1)

    # Setup logging
    log_level_argv = args.log_level.upper()
    log_level = getattr(logging, log_level_argv, logging.DEBUG)
    Application.log.setLevel(log_level)
    Application.log.debug(f'Set log level to: {log_level_argv}')

    # Fix and validate input path
    args.input_path = Application._try_fix_input_path(args.input_path or args.input_path_deprecated)

    if not args.create_project and not os.path.isfile(args.input_path):
        Application.log.error(f'Cannot load nonexistent PPJ at given path: "{args.input_path}"')
        sys.exit(1)

    # Handle .pex file special case (dump and exit)
    _, extension = os.path.splitext(os.path.basename(args.input_path).casefold())

    if extension == '.pex':
        header = PexReader.dump(args.input_path)
        Application.log.info(f'Dumping: "{args.input_path}"\n{header}')
        sys.exit(0)
    elif extension not in ('.ppj', '.pyroproject'):
        Application.log.error('Cannot proceed without PPJ file path')
        sys.exit(1)

    # Create project options and project
    options = ProjectOptions(args.__dict__)
    ppj = PapyrusProject(options)

    # Validate project file
    Application._validate_project_file(ppj)

    # Initialize remotes and imports if needed
    if ppj.scripts_node is not None or ppj.folders_node is not None or ppj.import_handler.remote_paths:
        ppj.try_initialize_remotes()

        if ppj.use_pre_import_event:
            ppj.try_run_event(ImportEvent.PRE)

        ppj.try_populate_imports()

        if ppj.use_post_import_event:
            ppj.try_run_event(ImportEvent.POST)

        ppj.try_set_game_type()
        ppj.find_missing_scripts()
        ppj.try_set_game_path()

        # Validate project paths
        Application._validate_project_paths(ppj)

        Application.log.info('Imports found:')
        for path in ppj.import_paths:
            Application.log.info(f'+ "{path}"')

        Application.log.info('Scripts found:')
        for _, path in ppj.psc_paths.items():
            Application.log.info(f'+ "{path}"')

    # Create build facade
    build_facade = BuildFacade(ppj)

    # Validate bsarch path (set during BuildFacade initialization)
    if ppj.options.package and not os.path.isfile(ppj.options.bsarch_path):
        Application.log.error('Cannot proceed with Package enabled without valid BSArch path')
        sys.exit(1)

    return Application(ppj, build_facade)
