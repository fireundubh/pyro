import argparse
import os

from GameType import GameType
from Index import Index
from Logger import Logger
from PapyrusProject import PapyrusProject
from Project import Project
from ProjectOptions import ProjectOptions
from TimeElapsed import TimeElapsed
from ValidationState import ValidationState


class CLI:
    @staticmethod
    def run(parser: argparse.ArgumentParser, logger: Logger) -> int:
        """Determine arguments and pass arguments to compiler"""

        args = parser.parse_args()

        # TODO: move arg validation elsewhere
        if args.show_help:
            parser.print_help()
            return 1

        # if required arguments not set, show help
        if args.game is None:
            logger.error('required argument missing: -g {tesv,fo4,sse}' + os.linesep)
            parser.print_help()
            return 1

        input_path = args.input

        if input_path is None:
            logger.error('required argument missing: -i INPUT' + os.linesep)
            parser.print_help()
            return 1

        if not input_path.endswith('.ppj'):
            logger.error('Single script compilation is no longer supported. Use a PPJ file.')
            parser.print_help()
            return 1

        if not os.path.isabs(input_path):
            logger.warn('Relative input path detected. Using current working directory: ' + os.getcwd())
            input_path = os.path.join(os.getcwd(), input_path.replace('file://', ''))
            logger.warn('Using input path: ' + input_path)

        _options = ProjectOptions()
        _options.disable_anonymizer = args.disable_anonymizer
        _options.disable_bsarch = args.disable_bsarch
        _options.disable_indexer = args.disable_indexer
        _options.game_type = GameType.from_str(args.game)
        _options.input_path = input_path

        _project = Project(_options)

        time_elapsed = TimeElapsed()

        ppj = PapyrusProject(_project)

        # the index is used to exclude unchanged scripts from compilation
        absolute_script_paths = ppj.get_script_paths(absolute_paths=True)
        file_name, file_extension = os.path.splitext(os.path.basename(ppj.input_path))
        project_index = Index(file_name, absolute_script_paths)

        ppj.compile_custom(project_index, time_elapsed)

        no_scripts_modified = False
        missing_scripts_found = False

        if _options.disable_indexer:
            pex_paths = ppj.get_script_paths_compiled()
        else:
            pex_paths, validation_states = ppj.validate_project(project_index, time_elapsed)
            no_scripts_modified = len(validation_states) == 1 and ValidationState.FILE_NOT_MODIFIED in validation_states
            missing_scripts_found = ValidationState.FILE_NOT_EXIST in validation_states

        if _options.disable_anonymizer:
            logger.warn('Anonymization disabled by user.')
        elif no_scripts_modified:
            logger.error('Cannot anonymize compiled scripts because no source scripts were modified')
        else:
            ppj.anonymize_scripts(pex_paths, ppj.output_path)

        if missing_scripts_found:
            logger.error('Cannot pack archive because there are missing scripts')
        else:
            ppj.pack_archive()

        time_elapsed.print()

        return 0
