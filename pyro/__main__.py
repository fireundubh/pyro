import argparse
import os
import sys
from urllib.parse import unquote_plus, urlparse

from pyro.BuildFacade import BuildFacade
from pyro.Logger import Logger
from pyro.PapyrusProject import PapyrusProject
from pyro.ProjectOptions import ProjectOptions
from pyro.PyroArgumentParser import PyroArgumentParser
from pyro.PyroRawDescriptionHelpFormatter import PyroRawTextHelpFormatter
from pyro.TimeElapsed import TimeElapsed


class Application(Logger):
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self._validate_args()

    # noinspection PyUnresolvedReferences
    @staticmethod
    def _url2pathname(url_path: str) -> str:
        url = urlparse(url_path)

        netloc: str = url.netloc
        path: str = url.path

        if netloc and netloc.startswith('/'):
            netloc = netloc[1:]

        if path and path.startswith('/'):
            path = path[1:]

        return os.path.normpath(unquote_plus(os.path.join(netloc, path)))

    def _validate_args(self) -> None:
        if self.args.show_help:
            sys.exit(print_help())

        input_path: str = self.args.input_path

        if not input_path:
            Application.log.error('required argument missing: -i INPUT.ppj')
            sys.exit(print_help())

        if not input_path.casefold().endswith('.ppj'):
            Application.log.error('Single script compilation is no longer supported. Use a PPJ file.')
            sys.exit(print_help())

        if input_path.casefold().startswith('file:'):
            full_path: str = Application._url2pathname(input_path)
            input_path = os.path.normpath(full_path)

        if not os.path.isabs(input_path):
            Application.log.warning('Using working directory: "%s"' % os.getcwd())
            input_path = os.path.join(os.getcwd(), input_path)
            Application.log.warning('Using input path: "%s"' % input_path)

        self.args.input_path = input_path

        if not os.path.exists(self.args.input_path):
            Application.log.error('Cannot load PPJ at given path because file does not exist: "%s"' % self.args.input_path)
            sys.exit(print_help())

    def run(self) -> int:
        options = ProjectOptions(self.args.__dict__)
        ppj = PapyrusProject(options)

        if not ppj.options.game_path:
            Application.log.error('Cannot determine game type from arguments or Papyrus Project')
            sys.exit(print_help())

        Application.log.info('Imports found:')
        for import_path in ppj.import_paths:
            Application.log.info('- "%s"' % import_path)

        Application.log.info('Scripts found:')
        for psc_path in ppj.psc_paths:
            Application.log.info('- "%s"' % psc_path)

        time_elapsed = TimeElapsed()

        build = BuildFacade(ppj)
        build.try_compile(time_elapsed)

        if ppj.options.anonymize:
            build.try_anonymize()
        else:
            Application.log.warning('Cannot anonymize scripts because anonymization was disabled by user')

        if ppj.options.bsarch and ppj.options.bsarch_path:
            build.try_pack()
        else:
            Application.log.warning('Cannot build package because packaging was disabled by user')

        time_elapsed.print(callback_func=Application.log.info)

        Application.log.info('DONE!')

        return 0


if __name__ == '__main__':
    _parser = PyroArgumentParser(add_help=False,
                                 formatter_class=PyroRawTextHelpFormatter,
                                 description=os.linesep.join([
                                     '-' * 80,
                                     ''.join([c.center(3) for c in 'PYRO']).center(80),
                                     '-' * 53 + ' github.com/fireundubh/pyro'
                                 ]))

    _required_arguments = _parser.add_argument_group('required arguments')
    _required_arguments.add_argument('-i', '--input-path',
                                     action='store', type=str,
                                     help='relative or absolute path to ppj file\n'
                                          '(if relative, must be relative to current working directory)')

    _build_arguments = _parser.add_argument_group('build arguments')
    _build_arguments.add_argument('--anonymize',
                                  action='store_true', default=False,
                                  help='anonymize metadata')
    _build_arguments.add_argument('--bsarch',
                                  action='store_true', default=False,
                                  help='create package with bsarch')
    _build_arguments.add_argument('--no-incremental-build',
                                  action='store_true', default=False,
                                  help='do not build incrementally')
    _build_arguments.add_argument('--no-parallel',
                                  action='store_true', default=False,
                                  help='do not parallelize compilation')
    _build_arguments.add_argument('--worker-limit',
                                  action='store', type=int,
                                  help='max workers for parallel compilation\n'
                                       '(usually set automatically to processor count)')

    _compiler_arguments = _parser.add_argument_group('compiler arguments')
    _compiler_arguments.add_argument('--compiler-path',
                                     action='store', type=str,
                                     help='relative or absolute path to PapyrusCompiler.exe\n'
                                          '(if relative, must be relative to current working directory)')
    _compiler_arguments.add_argument('--flags-path',
                                     action='store', type=str,
                                     help='relative or absolute path to Papyrus Flags file\n'
                                          '(if relative, must be relative to project)')
    _compiler_arguments.add_argument('--output-path',
                                     action='store', type=str,
                                     help='relative or absolute path to output folder\n'
                                          '(if relative, must be relative to project)')

    _game_arguments = _parser.add_argument_group('game arguments')
    _game_arguments.add_argument('-g', '--game-type',
                                 action='store', type=str,
                                 choices={'fo4', 'tesv', 'sse'},
                                 help='set game type (choices: fo4, tesv, sse)')

    _game_path_arguments = _game_arguments.add_mutually_exclusive_group()
    _game_path_arguments.add_argument('--game-path',
                                      action='store', type=str,
                                      help='relative or absolute path to game install directory\n'
                                           '(if relative, must be relative to current working directory)')
    if sys.platform == 'win32':
        _game_path_arguments.add_argument('--registry-path',
                                          action='store', type=str,
                                          help='path to Installed Path key in Windows Registry')

    _bsarch_arguments = _parser.add_argument_group('bsarch arguments')
    _bsarch_arguments.add_argument('--bsarch-path',
                                   action='store', type=str,
                                   help='relative or absolute path to bsarch.exe\n'
                                        '(if relative, must be relative to current working directory)')
    _bsarch_arguments.add_argument('--archive-path',
                                   action='store', type=str,
                                   help='relative or absolute path to bsa/ba2 file\n'
                                        '(if relative, must be relative to project)')
    _bsarch_arguments.add_argument('--temp-path',
                                   action='store', type=str,
                                   help='relative or absolute path to temp folder\n'
                                        '(if relative, must be relative to current working directory)')

    _program_arguments = _parser.add_argument_group('program arguments')
    _program_arguments.add_argument('--log-path',
                                    action='store', type=str,
                                    help='relative or absolute path to log folder\n'
                                         '(if relative, must be relative to current working directory)')
    _program_arguments.add_argument('--help', dest='show_help',
                                    action='store_true', default=False,
                                    help='show help and exit')


    def print_help() -> int:
        _parser.print_help()
        return 1


    Application(_parser.parse_args()).run()
