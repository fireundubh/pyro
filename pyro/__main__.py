import argparse
import os
import sys

from pyro.BuildFacade import BuildFacade
from pyro.Logger import Logger
from pyro.PapyrusProject import PapyrusProject
from pyro.ProjectOptions import ProjectOptions
from pyro.PyroArgumentParser import PyroArgumentParser
from pyro.PyroRawDescriptionHelpFormatter import PyroRawDescriptionHelpFormatter
from pyro.TimeElapsed import TimeElapsed


class Application:
    log = Logger()

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self._validate_args()

    def _validate_args(self) -> None:
        if self.args.show_help:
            sys.exit(print_help())

        if not self.args.input_path:
            self.log.error('required argument missing: -i INPUT.ppj')
            sys.exit(print_help())

        if not self.args.input_path.endswith('.ppj'):
            self.log.error('Single script compilation is no longer supported. Use a PPJ file.')
            sys.exit(print_help())

        if not os.path.isabs(self.args.input_path):
            self.log.warn('Using working directory: ' + os.getcwd())
            self.args.input_path = os.path.join(os.getcwd(), self.args.input_path.replace('file://', ''))
            self.log.warn('Using input path: ' + self.args.input_path)

    def run(self) -> int:
        options = ProjectOptions(self.args)
        ppj = PapyrusProject(options)

        # allow xml to set game type but defer to passed argument
        if not ppj.options.game_type:
            game_type = ppj.root_node.get('Game')
            if game_type:
                ppj.options.game_type = game_type

        ppj.options.game_path = ppj.get_game_path()

        if not ppj.options.game_path:
            self.log.error('Cannot determine game type from arguments or Papyrus Project')
            sys.exit(print_help())

        time_elapsed = TimeElapsed()

        build = BuildFacade(ppj)
        build.try_compile(time_elapsed)
        build.try_anonymize()
        build.try_pack()

        time_elapsed.print(callback_func=self.log.pyro)

        self.log.pyro('DONE!')

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
    _required_arguments.add_argument('-i', '--input-path',
                                     action='store', type=str,
                                     help='relative or absolute path to input ppj file')

    _build_arguments = _parser.add_argument_group('build arguments')
    _build_arguments.add_argument('--no-anonymize',
                                  action='store_true', default=False,
                                  help='do not anonymize metadata (if configured in ppj)')
    _build_arguments.add_argument('--no-bsarch',
                                  action='store_true', default=False,
                                  help='do not pack scripts with BSArch (if configured in ppj)')
    _build_arguments.add_argument('--no-incremental-build',
                                  action='store_true', default=False,
                                  help='do not build incrementally')
    _build_arguments.add_argument('--no-parallel',
                                  action='store_true', default=False,
                                  help='do not parallelize compilation')

    _compiler_arguments = _parser.add_argument_group('compiler arguments')
    _compiler_arguments.add_argument('--compiler-path',
                                     action='store', type=str,
                                     help='relative or absolute path to PapyrusCompiler.exe')
    _compiler_arguments.add_argument('--flags-path',
                                     action='store', type=str,
                                     help='relative or absolute path to Papyrus Flags file')
    _compiler_arguments.add_argument('--output-path',
                                     action='store', type=str,
                                     help='relative or absolute path to output folder')

    _game_arguments = _parser.add_argument_group('game arguments')
    _game_arguments.add_argument('-g', '--game-type',
                                 action='store', type=str,
                                 choices={'fo4', 'tesv', 'sse'},
                                 help='set game type (choices: fo4, tesv, sse)')

    _game_path_arguments = _game_arguments.add_mutually_exclusive_group()
    _game_path_arguments.add_argument('--game-path',
                                      action='store', type=str,
                                      help='relative or absolute path to game install directory')
    if sys.platform == 'win32':
        _game_path_arguments.add_argument('--registry-path',
                                          action='store', type=str,
                                          help='path to Installed Path key for game in Windows Registry')

    _bsarch_arguments = _parser.add_argument_group('bsarch arguments')
    _bsarch_arguments.add_argument('--bsarch-path',
                                   action='store', type=str,
                                   help='relative or absolute path to bsarch.exe')
    _bsarch_arguments.add_argument('--archive-path',
                                   action='store', type=str,
                                   help='relative or absolute path to zip file')
    _bsarch_arguments.add_argument('--temp-path',
                                   action='store', type=str,
                                   help='relative or absolute path to temp folder')

    _program_arguments = _parser.add_argument_group('program arguments')
    _program_arguments.add_argument('--log-path',
                                    action='store', type=str,
                                    help='relative or absolute path to log folder')
    _program_arguments.add_argument('--help', dest='show_help',
                                    action='store_true', default=False,
                                    help='show help and exit')


    def print_help() -> int:
        _parser.print_help()
        return 1


    Application(_parser.parse_args()).run()
