import argparse
import os
import sys

from pyro.BuildFacade import BuildFacade
from pyro.Logger import Logger
from pyro.PapyrusProject import PapyrusProject
from pyro.Project import Project
from pyro.ProjectOptions import ProjectOptions
from pyro.PyroArgumentParser import PyroArgumentParser
from pyro.PyroRawDescriptionHelpFormatter import PyroRawDescriptionHelpFormatter
from pyro.TimeElapsed import TimeElapsed


class Application:
    @staticmethod
    def run(args: argparse.Namespace) -> int:
        """Determine arguments and pass arguments to compiler"""

        logger = Logger()

        if args.show_help:
            return print_help()

        if not args.input_path:
            logger.error('required argument missing: -i INPUT.ppj' + os.linesep)
            return print_help()

        if not args.input_path.endswith('.ppj'):
            logger.error('Single script compilation is no longer supported. Use a PPJ file.')
            return print_help()

        if not os.path.isabs(args.input_path):
            logger.warn('Relative input path detected. Using current working directory: ' + os.getcwd())
            args.input_path = os.path.join(os.getcwd(), args.input_path.replace('file://', ''))
            logger.warn('Using input path: ' + args.input_path)

        project_options = ProjectOptions(args)
        project = Project(project_options)

        time_elapsed = TimeElapsed()

        ppj = PapyrusProject(project)

        build = BuildFacade(ppj)
        build.try_compile(time_elapsed)
        build.try_anonymize()
        build.try_pack()

        time_elapsed.print()

        return 0


if __name__ == '__main__':
    _parser = PyroArgumentParser(add_help=False,
                                 formatter_class=PyroRawDescriptionHelpFormatter,
                                 description=os.linesep.join([
                                     'Pyro CLI by fireundubh',
                                     'A semi-automated incremental build system for TESV, SSE, and FO4 projects'
                                 ]),
                                 epilog='For more help, visit: github.com/fireundubh/pyro')

    _required_arguments = _parser.add_argument_group('required arguments')
    _required_arguments.add_argument('-g', '--game-type',
                                     action='store', type=str,
                                     choices={'fo4', 'tesv', 'sse'},
                                     help='set game type (choices: fo4, tesv, sse)')
    _required_arguments.add_argument('-i', '--input-path',
                                     action='store', type=str,
                                     help='relative or absolute path to input ppj file')

    _optional_arguments = _parser.add_argument_group('optional arguments')
    _optional_arguments.add_argument('--disable-anonymizer',
                                     action='store_true', default=False,
                                     help='do not anonymize script metadata (if configured in ppj)')
    _optional_arguments.add_argument('--disable-bsarch',
                                     action='store_true', default=False,
                                     help='do not pack scripts with BSArch (if configured in ppj)')
    _optional_arguments.add_argument('--disable-incremental-build',
                                     action='store_true', default=False,
                                     help='do not build incrementally')
    _optional_arguments.add_argument('--disable-parallel',
                                     action='store_true', default=False,
                                     help='do not parallelize compilation')

    _compiler_arguments = _parser.add_argument_group('compiler arguments')
    _compiler_arguments.add_argument('--compiler-path',
                                     action='store', type=str,
                                     help='relative path from game to PapyrusCompiler.exe')
    _compiler_arguments.add_argument('--flags-path',
                                     action='store', type=str,
                                     help='relative path from game to Papyrus flags file')
    _compiler_arguments.add_argument('--source-path',
                                     action='store', type=str,
                                     help='relative path from game to script sources folder')
    _compiler_arguments.add_argument('--base-path',
                                     action='store', type=str,
                                     help='relative path from game to base script sources folder')
    _compiler_arguments.add_argument('--user-path',
                                     action='store', type=str,
                                     help='relative path from game to user script sources folder')

    _game_arguments = _parser.add_argument_group('game arguments')
    _game_arguments.add_argument('--game-path',
                                 action='store', type=str,
                                 help='absolute path to installation directory for game')

    if sys.platform == 'win32':
        _game_arguments.add_argument('--registry-path',
                                     action='store', type=str,
                                     help='path to Installed Path key for game in Windows Registry')

    _tool_arguments = _parser.add_argument_group('tool arguments')
    _tool_arguments.add_argument('--bsarch-path',
                                 action='store', type=str,
                                 help='relative or absolute path to BSArch.exe')

    _program_arguments = _parser.add_argument_group('program arguments')
    _program_arguments.add_argument('--temp-path',
                                    action='store', type=str,
                                    help='relative or absolute path to temp folder')
    _program_arguments.add_argument('--help', dest='show_help',
                                    action='store_true', default=False,
                                    help='show help and exit')


    def print_help() -> int:
        _parser.print_help()
        return 1


    Application.run(_parser.parse_args())
