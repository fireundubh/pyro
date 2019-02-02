#!/usr/bin/env python3
# coding=utf-8

import argparse
import os
import subprocess
import sys
import time

try:
    from lxml import etree
except ImportError:
    subprocess.call([sys.executable, '-m', 'pip', 'install', 'lxml'])
    # noinspection PyUnresolvedReferences
    from lxml import etree

from Arguments import Arguments
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

    time_elapsed = TimeElapsed()

    if not compile_project:
        compile_script(project, args.skip_output_validation, time_elapsed)
    else:
        if project.is_fallout4:
            compile_ppj_native(project, args.quiet, args.skip_output_validation, time_elapsed)
        else:
            compile_ppj_custom(project, args.quiet, args.skip_output_validation, time_elapsed)

    time_elapsed.print()


def compile_script(prj: Project, skip_validation: bool, time_elapsed: TimeElapsed) -> None:
    arguments = Arguments()

    imports = [prj.get_scripts_user_path(), prj.get_scripts_base_path()]
    if not prj.is_fallout4:
        imports.insert(0, os.path.dirname(prj.input_path))

    imports = ';'.join(map(lambda x: x if os.path.exists(x) else '', imports))

    arguments.append_quoted(prj.get_compiler_path())
    if prj.namespace:
        arguments.append_quoted(os.path.join(prj.namespace, os.path.basename(prj.input_path)))
    else:
        arguments.append_quoted(prj.input_path)
    arguments.append_quoted(prj.try_parse_relative_output_path(), 'o')
    arguments.append_quoted(imports, 'i')
    arguments.append_quoted(os.path.basename(prj.get_flags_path()), 'f')

    if args.quiet:
        arguments.append('-q')

    if os.path.isdir(args.input):
        arguments.append('-all')

    print(arguments.join())

    process = subprocess.Popen(arguments.join(), stdout=subprocess.PIPE, shell=False, universal_newlines=True)

    time_elapsed.start_time = time.time()

    process.wait()

    time_elapsed.end_time = time.time()

    if not skip_validation:
        _, output_file_name = os.path.split(prj.input_path)

        if prj.is_fallout4 and prj.USER_PATH_PART in prj.input_path.casefold():
            output_file_name = os.path.join(prj.namespace, os.path.basename(prj.input_path))

        output_file_name = output_file_name.replace('.psc', '.pex')
        output_file_path = os.path.join(prj.try_parse_relative_output_path(), output_file_name)

        prj.validate_script(output_file_path, time_elapsed)


def compile_ppj_native(prj: Project, quiet: bool, skip_validation: bool, time_elapsed: TimeElapsed) -> None:
    game_path = prj.get_game_path()

    compiler_path = prj.get_compiler_path()

    project_args = [os.path.join(game_path, compiler_path), prj.input_path]

    if quiet:
        project_args.append('-q')

    time_elapsed.start_time = time.time()

    PapyrusProject.open_process(project_args)

    time_elapsed.end_time = time.time()

    if not skip_validation:
        ppj = PapyrusProject(prj)
        ppj.validate_project(time_elapsed)


def compile_ppj_custom(prj: Project, quiet: bool, skip_validation: bool, time_elapsed: TimeElapsed) -> None:
    ppj = PapyrusProject(prj)

    time_elapsed.start_time = time.time()

    ppj.compile(prj.output_path, quiet)

    time_elapsed.end_time = time.time()

    if not skip_validation:
        ppj.validate_project(time_elapsed)


if __name__ == '__main__':
    if not os.path.exists(os.path.join(os.path.dirname(__file__), 'pyro.ini')):
        raise FileNotFoundError('Cannot proceed without pyro.ini configuration file')

    parser = argparse.ArgumentParser(add_help=False)

    _required_arguments = parser.add_argument_group('required arguments')
    _required_arguments.add_argument('-g', action='store', dest='game', choices={'fo4', 'sse', 'tesv'}, help='set compiler version')
    _required_arguments.add_argument('-i', action='store', dest='input', help='absolute path to input file or folder')

    _optional_arguments = parser.add_argument_group('optional arguments')
    _optional_arguments.add_argument('-ns', action='store', dest='namespace', default='', help='namespace for single script compilation (fo4)')
    _optional_arguments.add_argument('-o', action='store', dest='output', default='..', help='absolute path to output folder (default: ..)')
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

    project = Project(GameType.from_str(args.game), args.input, args.output, args.namespace)

    main()
