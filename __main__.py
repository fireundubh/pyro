#!/usr/bin/env python3
# coding=utf-8

import argparse
import os
import platform
import subprocess
import sys
import time

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

    time_elapsed = TimeElapsed()

    if not compile_project:
        compile_script(project, args.skip_output_validation, time_elapsed)
    else:
        if project.game_type == GameType.Fallout4:
            compile_ppj_native(project, args.quiet, args.skip_output_validation, time_elapsed)
        else:
            compile_ppj_custom(project, args.quiet, args.skip_output_validation, time_elapsed)

    time_elapsed.print()


def compile_script(prj: Project, skip_validation: bool, time_elapsed: TimeElapsed):
    compiler_args = [
        '%s' % prj.compiler_path,
        '%s' % prj.input_path,
        '-o=%s' % prj.try_parse_relative_output_path(),
        '-i=%s' % '',
        '-f=%s' % prj.flags_path
    ]

    if args.quiet:
        compiler_args.append('-q')

    if os.path.isdir(args.input):
        compiler_args.append('-all')

    process = subprocess.Popen(compiler_args, stdout=subprocess.PIPE, shell=False, universal_newlines=True)

    time_elapsed.start_time = time.time()

    process.wait()

    time_elapsed.end_time = time.time()

    if not skip_validation:
        _, output_file_name = os.path.split(prj.input_path)

        if prj.game_type == GameType.Fallout4 and prj.USER_PATH_PART in prj.input_path.casefold():
            output_file_name = os.path.join(*prj.input_path.split('\\')[-2:])

        output_file_name = output_file_name.replace('.psc', '.pex')
        validate_script_output(os.path.join(prj.output_path, output_file_name), time_elapsed)


def compile_ppj_native(prj: Project, quiet: bool, skip_validation: bool, time_elapsed: TimeElapsed):
    project_args = [os.path.join(prj.get_game_path, prj.compiler_path), prj.input_path, '-q' if quiet else None]

    process = subprocess.Popen(project_args, shell=False, universal_newlines=True)

    time_elapsed.start_time = time.time()

    process.wait()

    time_elapsed.end_time = time.time()

    if not skip_validation:
        ppj = PapyrusProject(prj)
        validate_ppj_output(ppj, time_elapsed)


def compile_ppj_custom(prj: Project, quiet: bool, skip_validation: bool, time_elapsed: TimeElapsed):
    ppj = PapyrusProject(prj)

    time_elapsed.start_time = time.time()

    ppj.compile(prj.output_path, quiet)

    time_elapsed.end_time = time.time()

    if not skip_validation:
        validate_ppj_output(ppj, time_elapsed)


def validate_script_output(script_path: str, time_elapsed: TimeElapsed) -> None:
    if not os.path.exists(script_path):
        return print('[PYRO] Failed to write file: ' + script_path + ' (file does not exist)')

    if time_elapsed.start_time < os.stat(script_path).st_mtime < time_elapsed.end_time:
        return print('[PYRO] Wrote file:', script_path)

    print('[PYRO] Failed to write file: ' + script_path + ' (not recently modified)')


def validate_ppj_output(ppj: PapyrusProject, time_elapsed: TimeElapsed) -> None:
    output_path = ppj.get_output_path()

    script_paths = [os.path.join(output_path, script.replace('.psc', '.pex')) for script in ppj.get_script_paths()]

    if ppj.game_type != GameType.Fallout4:
        script_paths = [os.path.join(output_path, os.path.basename(script)) for script in script_paths]

    for script_path in script_paths:
        validate_script_output(script_path, time_elapsed)


if __name__ == '__main__':
    if platform.system() != 'Windows':
        raise OSError('Cannot run on non-Windows platform due to use of Windows Registry to determine paths')

    PROGRAM_PATH = os.path.abspath(os.path.dirname(__file__))

    if not os.path.exists(os.path.join(PROGRAM_PATH, 'pyro.ini')):
        raise FileNotFoundError('Cannot proceed without pyro.ini configuration file')

    parser = argparse.ArgumentParser(add_help=False)

    _required_arguments = parser.add_argument_group('required arguments')
    _required_arguments.add_argument('-g', action='store', dest='game', choices={'fo4', 'sse', 'tesv'}, help='set compiler version')
    _required_arguments.add_argument('-i', action='store', dest='input', help='set absolute path to input file or folder')

    _optional_arguments = parser.add_argument_group('optional arguments')
    _optional_arguments.add_argument('-o', action='store', dest='output', default='..', help='set absolute path to output folder (default: ..)')
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

    project = Project(GameType.from_str(args.game), args.input, args.output)

    main()
