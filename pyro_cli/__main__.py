import argparse
import os

from pyro.Indexer import Indexer
from pyro.Logger import Logger
from pyro.PapyrusProject import PapyrusProject
from pyro.Project import Project
from pyro.ProjectOptions import ProjectOptions
from pyro.TimeElapsed import TimeElapsed
from pyro.enums import GameType, ValidationState


class Application:
    @staticmethod
    def run(args: argparse.Namespace) -> int:
        """Determine arguments and pass arguments to compiler"""

        logger = Logger()

        if not os.path.exists(args.conf):
            return logger.error('Cannot proceed without pyro.ini configuration file')

        if args.show_help:
            return print_help()

        # if required arguments not set, show help
        if args.game is None:
            logger.error('required argument missing: -g {tesv,fo4,sse}' + os.linesep)
            return print_help()

        input_path = args.input

        if input_path is None:
            logger.error('required argument missing: -i INPUT.ppj' + os.linesep)
            return print_help()

        if not input_path.endswith('.ppj'):
            logger.error('Single script compilation is no longer supported. Use a PPJ file.')
            return print_help()

        if not os.path.isabs(input_path):
            logger.warn('Relative input path detected. Using current working directory: ' + os.getcwd())
            input_path = os.path.join(os.getcwd(), input_path.replace('file://', ''))
            logger.warn('Using input path: ' + input_path)

        project_options = ProjectOptions()
        project_options.pyro_cfg_path = args.conf
        project_options.disable_anonymizer = args.disable_anonymizer
        project_options.disable_bsarch = args.disable_bsarch
        project_options.disable_indexer = args.disable_indexer
        project_options.disable_parallel = args.disable_parallel
        project_options.game_type = GameType.from_str(args.game)
        project_options.input_path = input_path

        project = Project(project_options)

        time_elapsed = TimeElapsed()

        ppj = PapyrusProject(project)

        # the index is used to exclude unchanged scripts from compilation
        absolute_script_paths = ppj.get_script_paths(absolute_paths=True)
        file_name, file_extension = os.path.splitext(os.path.basename(ppj.input_path))
        project_index = Indexer(project, file_name, absolute_script_paths)

        ppj.compile_custom(project_index, time_elapsed)

        no_scripts_modified = False
        missing_scripts_found = False

        if project_options.disable_indexer:
            pex_paths = ppj.get_script_paths_compiled()
        else:
            pex_paths, validation_states = ppj.validate_project(project_index, time_elapsed)
            no_scripts_modified = len(validation_states) == 1 and ValidationState.FILE_NOT_MODIFIED in validation_states
            missing_scripts_found = ValidationState.FILE_NOT_EXIST in validation_states

        if project_options.disable_anonymizer:
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


if __name__ == '__main__':
    _parser = argparse.ArgumentParser(add_help=False, description='Pyro CLI by fireundubh')

    _required_arguments = _parser.add_argument_group('required arguments')

    _required_arguments.add_argument('-g', dest='game',
                                     action='store', choices={'fo4', 'tesv', 'sse'},
                                     help='set compiler version')

    _required_arguments.add_argument('-i', dest='input',
                                     action='store',
                                     help='absolute path to input ppj file')

    _optional_arguments = _parser.add_argument_group('optional arguments')

    _optional_arguments.add_argument('-c', dest='conf',
                                     action='store', default=os.path.join(os.path.dirname(__file__), 'pyro.ini'),
                                     help='absolute path to pyro.ini')
    _optional_arguments.add_argument('--disable-anonymizer',
                                     action='store_true', default=False,
                                     help='do not anonymize script metadata (if configured in ppj)')
    _optional_arguments.add_argument('--disable-bsarch',
                                     action='store_true', default=False,
                                     help='do not pack scripts with BSArch (if configured in ppj)')
    _optional_arguments.add_argument('--disable-indexer',
                                     action='store_true', default=False,
                                     help='do not index scripts')
    _optional_arguments.add_argument('--disable-parallel',
                                     action='store_true', default=False,
                                     help='disable parallellization (for debugging)')

    _program_arguments = _parser.add_argument_group('program arguments')

    _program_arguments.add_argument('--help', dest='show_help',
                                    action='store_true', default=False,
                                    help='show help and exit')


    def print_help() -> int:
        _parser.print_help()
        return 1


    Application.run(_parser.parse_args())
