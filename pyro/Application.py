import argparse
import json
import logging
import os
import sys
from typing import List

from pyro.Enums.Event import (BuildEvent,
                              ImportEvent,
                              CompileEvent,
                              AnonymizeEvent,
                              PackageEvent,
                              ZipEvent)
from pyro.BuildFacade import BuildFacade
from pyro.Comparators import startswith
from pyro.PapyrusProject import PapyrusProject
from pyro.PathHelper import PathHelper
from pyro.PexReader import PexReader
from pyro.ProjectOptions import ProjectOptions


class Application:
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s [%(levelname).4s] %(message)s')
    log = logging.getLogger('pyro')

    args: argparse.Namespace = None

    def __init__(self, parser: argparse.ArgumentParser) -> None:
        self.parser = parser

        self.args = self.parser.parse_args()

        if self.args.show_help:
            self.parser.print_help()
            sys.exit(1)

        # Quiet logging for output commands
        if self.args.resolve_project or self.args.resolve_project_scripts:
            Application.log.setLevel('ERROR')
        self.args.input_path = self._try_fix_input_path(self.args.input_path or self.args.input_path_deprecated)

        if not self.args.create_project and not os.path.isfile(self.args.input_path):
            Application.log.error(f'Cannot load nonexistent PPJ at given path: "{self.args.input_path}"')
            sys.exit(1)

    @staticmethod
    def _try_fix_input_path(input_path: str) -> str:
        if not input_path:
            Application.log.error('required argument missing: -i INPUT.ppj')
            sys.exit(1)

        if startswith(input_path, 'file:', ignorecase=True):
            full_path = PathHelper.url2pathname(input_path)
            input_path = os.path.normpath(full_path)

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

    @staticmethod
    def populate_project(ppj: PapyrusProject) -> bool:
        if ppj.scripts_node is not None or ppj.folders_node is not None or ppj.remote_paths:
            ppj.try_initialize_remotes()

            if ppj.use_pre_import_event:
                ppj.try_run_event(ImportEvent.PRE)

            ppj.try_populate_imports()

            if ppj.use_post_import_event:
                ppj.try_run_event(ImportEvent.POST)

            ppj.try_set_game_type()
            ppj.find_missing_scripts()
            ppj.try_set_game_path()
            return True
        return False

    @staticmethod
    def get_json_blob(ppj: PapyrusProject) -> str:
        if not Application.populate_project(ppj):
            return ""
        project_info = dict[str, any]()
        project_info["name"] = ppj.project_name
        project_info["path"] = ppj.project_path
        project_info["flags_path"] = ppj.get_flags_path()
        project_info["output_path"] = ppj.get_output_path()
        project_info["package_path"] = ppj.get_package_path()
        import_script_infos: List[dict[str, str]] = []
        project_script_infos: List[dict[str, str]] = []

        for object_name, script_path in ppj._get_import_psc_paths(True).items():
            import_script_info = dict[str, str]()
            import_script_info["name"] = object_name.removesuffix(".psc").replace(os.path.sep, ":")
            import_script_info["source_path"] = script_path
            import_script_infos.append(import_script_info)
        project_info["imported_scripts"] = import_script_infos

        for object_name, script_path in ppj.psc_paths.items():
            project_script_info = dict[str, str]()
            project_script_info["name"] = object_name.removesuffix(".psc").replace(os.path.sep, ":")
            project_script_info["source_path"] = script_path
            project_script_info["output_path"] = ppj._get_pex_path(object_name)
            project_script_infos.append(project_script_info)
        project_info["project_scripts"] = project_script_infos
        return json.dumps(project_info, indent=4)

    def run(self) -> int:
        """
        Entry point
        """
        _, extension = os.path.splitext(os.path.basename(self.args.input_path).casefold())

        if extension == '.pex':
            header = PexReader.dump(self.args.input_path)
            Application.log.info(f'Dumping: "{self.args.input_path}"\n{header}')
            sys.exit(0)
        elif extension not in ('.ppj', '.pyroproject'):
            Application.log.error('Cannot proceed without PPJ file path')
            sys.exit(1)

        options = ProjectOptions(self.args.__dict__)
        ppj = PapyrusProject(options)

        self._validate_project_file(ppj)
        if options.resolve_project_scripts:
            print(self.get_json_blob(ppj))
            sys.exit(0)

        if self.populate_project(ppj):
            self._validate_project_paths(ppj)

            Application.log.info('Imports found:')
            for path in ppj.import_paths:
                Application.log.info(f'+ "{path}"')

            Application.log.info('Scripts found:')
            for _, path in ppj.psc_paths.items():
                Application.log.info(f'+ "{path}"')

        build = BuildFacade(ppj)

        # bsarch path is not set until BuildFacade initializes
        if ppj.options.package and not os.path.isfile(ppj.options.bsarch_path):
            Application.log.error('Cannot proceed with Package enabled without valid BSArch path')
            sys.exit(1)

        if ppj.use_pre_build_event:
            ppj.try_run_event(BuildEvent.PRE)

        if build.scripts_count > 0:
            if ppj.use_pre_compile_event:
                ppj.try_run_event(CompileEvent.PRE)

            build.try_compile()

            if ppj.use_post_compile_event:
                ppj.try_run_event(CompileEvent.POST)

            if ppj.options.anonymize:
                if build.compile_data.failed_count == 0 or ppj.options.ignore_errors:
                    if ppj.use_pre_anonymize_event:
                        ppj.try_run_event(AnonymizeEvent.PRE)

                    build.try_anonymize()

                    if ppj.use_post_anonymize_event:
                        ppj.try_run_event(AnonymizeEvent.POST)
                else:
                    Application.log.error(f'Cannot anonymize scripts because {build.compile_data.failed_count} scripts failed to compile')
                    sys.exit(build.compile_data.failed_count)
            else:
                Application.log.info('Cannot anonymize scripts because Anonymize is disabled in project')

        if ppj.options.package:
            if build.compile_data.failed_count == 0 or ppj.options.ignore_errors:
                if ppj.use_pre_package_event:
                    ppj.try_run_event(PackageEvent.PRE)

                build.try_pack()

                if ppj.use_post_package_event:
                    ppj.try_run_event(PackageEvent.POST)
            else:
                Application.log.error(f'Cannot create Packages because {build.compile_data.failed_count} scripts failed to compile')
                sys.exit(build.compile_data.failed_count)
        elif ppj.packages_node is not None:
            Application.log.info('Cannot create Packages because Package is disabled in project')

        if ppj.options.zip:
            if build.compile_data.failed_count == 0 or ppj.options.ignore_errors:
                if ppj.use_pre_zip_event:
                    ppj.try_run_event(ZipEvent.PRE)

                build.try_zip()

                if ppj.use_post_zip_event:
                    ppj.try_run_event(ZipEvent.POST)
            else:
                Application.log.error(f'Cannot create ZipFile because {build.compile_data.failed_count} scripts failed to compile')
                sys.exit(build.compile_data.failed_count)
        elif ppj.zip_files_node is not None:
            Application.log.info('Cannot create ZipFile because Zip is disabled in project')

        if build.scripts_count > 0:
            Application.log.info(build.compile_data.to_string() if build.compile_data.success_count > 0 else 'No scripts were compiled.')

        if ppj.packages_node is not None:
            Application.log.info(build.package_data.to_string() if build.package_data.file_count > 0 else 'No files were packaged.')

        if ppj.zip_files_node is not None:
            Application.log.info(build.zipping_data.to_string() if build.zipping_data.file_count > 0 else 'No files were zipped.')

        Application.log.info('DONE!')

        if ppj.use_post_build_event and build.compile_data.failed_count == 0:
            ppj.try_run_event(BuildEvent.POST)

        return build.compile_data.failed_count
