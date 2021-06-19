import os
import sys
from argparse import SUPPRESS

from pyro.Application import Application
from pyro.PyroArgumentParser import PyroArgumentParser
from pyro.PyroRawDescriptionHelpFormatter import PyroRawTextHelpFormatter

if __name__ == '__main__':
    # noinspection PyTypeChecker
    _parser = PyroArgumentParser(add_help=False,
                                 formatter_class=PyroRawTextHelpFormatter,
                                 description=os.linesep.join([
                                     '-' * 80,
                                     ''.join(c.center(3) for c in 'PYRO').center(80),
                                     '-' * 53 + ' github.com/fireundubh/pyro'
                                 ]))

    _required_arguments = _parser.add_argument_group('required arguments')
    _required_arguments_flex = _required_arguments.add_mutually_exclusive_group()
    _required_arguments_flex.add_argument('input_path', nargs='?',
                                          action='store', type=str,
                                          help='relative or absolute path to file\n'
                                               '(if relative, must be relative to current working directory)')
    # deprecated argument format (retained to avoid breaking change)
    _required_arguments_flex.add_argument('-i', '--input-path', dest='input_path_deprecated',
                                          action='store', type=str,
                                          help=SUPPRESS)

    _build_arguments = _parser.add_argument_group('build arguments')
    _build_arguments.add_argument('--ignore-errors',
                                  action='store_true', default=False,
                                  help='ignore compiler errors during build')
    _build_arguments.add_argument('--no-implicit-imports',
                                  action='store_true', default=False,
                                  help='do not build with implicit imports')
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
                                 choices=('fo4', 'tes5', 'sse'),
                                 help='set game type (choices: fo4, tes5, sse)')

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
    _bsarch_arguments.add_argument('--package-path',
                                   action='store', type=str,
                                   help='relative or absolute path to bsa/ba2 output folder\n'
                                        '(if relative, must be relative to project)')
    _bsarch_arguments.add_argument('--temp-path',
                                   action='store', type=str,
                                   help='relative or absolute path to temp folder\n'
                                        '(if relative, must be relative to current working directory)')

    _zip_arguments = _parser.add_argument_group('zip arguments')
    _zip_arguments.add_argument('--zip-compression',
                                action='store', type=str,
                                choices=('store', 'deflate'),
                                help='set compression method (choices: store, deflate)')
    _zip_arguments.add_argument('--zip-output-path',
                                action='store', type=str,
                                help='relative or absolute path to zip output folder\n'
                                     '(if relative, must be relative to project)')

    _remote_arguments = _parser.add_argument_group('remote arguments')
    _remote_arguments.add_argument('--access-token',
                                   action='store', type=str,
                                   help='access token for GitHub remotes\n(must have public_repo access scope)')
    _remote_arguments.add_argument('--force-overwrite',
                                   action='store_true',
                                   help='download remote files and overwrite existing files\n'
                                        '(default: do not redownload unchanged files)')
    _remote_arguments.add_argument('--remote-temp-path',
                                   action='store', type=str,
                                   help='relative or absolute path to temp folder for remote files\n'
                                        '(if relative, must be relative to project)')

    _project_arguments = _parser.add_argument_group('project arguments')
    _project_arguments.add_argument('--create-project',
                                    action='store_true',
                                    help='generate project from current directory')
    _project_arguments.add_argument('--resolve-project',
                                    action='store_true',
                                    help='resolve variables and paths in project file')

    _program_arguments = _parser.add_argument_group('program arguments')
    _program_arguments.add_argument('--help', dest='show_help',
                                    action='store_true', default=False,
                                    help='show help and exit')

    Application(_parser).run()
