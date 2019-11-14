import argparse
import os

from pyro.BuildFacade import BuildFacade
from pyro.Logger import Logger
from pyro.PapyrusProject import PapyrusProject
from pyro.Project import Project
from pyro.ProjectOptions import ProjectOptions
from pyro.TimeElapsed import TimeElapsed
from pyro_cli.PyroArgumentParser import PyroArgumentParser


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
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description=os.linesep.join([
                                     'Pyro CLI by fireundubh',
                                     'A semi-automated incremental build system for TESV, SSE, and FO4 projects'
                                 ]),
                                 epilog='For more help, visit: github.com/fireundubh/pyro')

    _required_arguments = _parser.add_argument_group('required arguments')
    _required_arguments.add_argument('-g', dest='game_type',
                                     action='store', choices={'fo4', 'tesv', 'sse'},
                                     help='set compiler version')
    _required_arguments.add_argument('-i', dest='input_path',
                                     action='store',
                                     help='absolute path to input ppj file')

    _optional_arguments = _parser.add_argument_group('optional arguments')
    _optional_arguments.add_argument('--disable-anonymizer',
                                     action='store_true', default=False,
                                     help='do not anonymize script metadata (if configured in ppj)')
    _optional_arguments.add_argument('--disable-bsarch',
                                     action='store_true', default=False,
                                     help='do not pack scripts with BSArch (if configured in ppj)')
    _optional_arguments.add_argument('--disable-parallel',
                                     action='store_true', default=False,
                                     help='do not parallelize compilation')

    _program_arguments = _parser.add_argument_group('program arguments')

    _program_arguments.add_argument('--help', dest='show_help',
                                    action='store_true', default=False,
                                    help='show help and exit')

    def print_help() -> int:
        _parser.print_help()
        return 1

    Application.run(_parser.parse_args())
