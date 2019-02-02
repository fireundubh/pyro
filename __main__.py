#!/usr/bin/env python3
# coding=utf-8

import argparse
import os
import subprocess
import sys

try:
    from lxml import etree
except ImportError:
    subprocess.call([sys.executable, '-m', 'pip', 'install', 'lxml'])
    # noinspection PyUnresolvedReferences
    from lxml import etree

from GameType import GameType
from PapyrusProject import PapyrusProject
from Project import Project
from TimeElapsed import TimeElapsed

__version__ = 'pyro-1.3 by fireundubh <github.com/fireundubh>'


def main():
    """Determine arguments and pass arguments to compiler"""
    compile_project = False

    if os.path.isfile(args.input):
        _, file_extension = os.path.splitext(args.input)
        compile_project = file_extension == '.ppj'

    if not compile_project:
        sys.tracebacklimit = 0
        raise ValueError('Single script compilation is no longer supported. Use a PPJ file.')
    else:
        time_elapsed = TimeElapsed()

        ppj = PapyrusProject(project)

        if project.is_fallout4:
            ppj.compile_native(args.quiet, time_elapsed)
        else:
            ppj.compile_custom(args.quiet, time_elapsed)

        if not args.skip_output_validation:
            ppj.validate_project(time_elapsed)

        time_elapsed.print()


if __name__ == '__main__':
    if not os.path.exists(os.path.join(os.path.dirname(__file__), 'pyro.ini')):
        raise FileNotFoundError('Cannot proceed without pyro.ini configuration file')

    parser = argparse.ArgumentParser(add_help=False)

    _required_arguments = parser.add_argument_group('required arguments')
    _required_arguments.add_argument('-g', action='store', dest='game', choices={'fo4', 'sse', 'tesv'}, help='set compiler version')
    _required_arguments.add_argument('-i', action='store', dest='input', help='absolute path to input file or folder')

    _optional_arguments = parser.add_argument_group('optional arguments')
    _optional_arguments.add_argument('-q', action='store_true', dest='quiet', default=False, help='report only compiler failures')
    _optional_arguments.add_argument('-s', action='store_true', dest='skip_output_validation', default=False, help='skip output validation')

    _program_arguments = parser.add_argument_group('program arguments')
    _program_arguments.add_argument('--help', action='store_true', dest='show_help', default=False, help='show help and exit')
    _program_arguments.add_argument('--version', action='version', version='%s' % __version__)

    args = parser.parse_args()

    if args.show_help:
        exit(parser.print_help())

    # if required arguments not set, show help
    if args.game is None:
        print('[ERROR] required argument missing: -g {tesv,fo4,sse}' + os.linesep)
        exit(parser.print_help())

    if args.input is None:
        print('[ERROR] required argument missing: -i INPUT' + os.linesep)
        exit(parser.print_help())

    project = Project(GameType.from_str(args.game), args.input)

    main()
