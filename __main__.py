#!/usr/bin/env python3
# coding=utf-8

import argparse
import os
import subprocess
import sys
from collections import namedtuple

try:
    from lxml import etree
except ImportError:
    subprocess.call([sys.executable, '-m', 'pip', 'install', 'lxml'])
    # noinspection PyUnresolvedReferences
    from lxml import etree

from GameType import GameType
from Index import Index
from Logger import Logger
from PapyrusProject import PapyrusProject
from Project import Project
from TimeElapsed import TimeElapsed
from ValidationState import ValidationState

__version__ = 'pyro-1.3 by fireundubh <github.com/fireundubh>'


def main():
    """Determine arguments and pass arguments to compiler"""

    _options = namedtuple('ProjectOptions', 'game_type input_path disable_anonymizer disable_bsarch disable_indexer')
    _options.disable_anonymizer = _args.disable_anonymizer
    _options.disable_bsarch = _args.disable_bsarch
    _options.disable_indexer = _args.disable_indexer
    _options.game_type = GameType.from_str(_args.game)
    _options.input_path = _args.input

    _project = Project(_options)

    time_elapsed = TimeElapsed()

    ppj = PapyrusProject(_project)

    # the index is used to exclude unchanged scripts from compilation
    absolute_script_paths = ppj.get_script_paths(absolute_paths=True)
    file_name, file_extension = os.path.splitext(os.path.basename(ppj.input_path))
    project_index = Index(file_name, absolute_script_paths)

    ppj.compile_custom(project_index, time_elapsed)

    validated_paths, validation_states = ppj.validate_project(project_index, time_elapsed)
    no_changed_files = len(validation_states) == 1 and ValidationState.FILE_NOT_MODIFIED in validation_states

    if no_changed_files:
        log.error('Cannot anonymize compiled scripts because no source scripts were modified')
    elif len(validated_paths) > 0:
        ppj.anonymize_scripts(validated_paths, ppj.output_path)

    archive_path = ppj.root_node.get('Archive')

    if len(validated_paths) == 0:
        log.error('Cannot pack archive because no scripts were found')
    elif ValidationState.FILE_NOT_EXIST in validation_states:
        log.error('Cannot pack archive because there are missing scripts')
    elif os.path.exists(archive_path) and no_changed_files:
        log.error('Cannot pack archive because archive exists and no source scripts were modified')
    else:
        ppj.pack_archive()

    time_elapsed.print()


if __name__ == '__main__':
    log = Logger()

    if not os.path.exists(os.path.join(os.path.dirname(__file__), 'pyro.ini')):
        exit(log.error('Cannot proceed without pyro.ini configuration file'))

    _parser = argparse.ArgumentParser(add_help=False)

    _required_arguments = _parser.add_argument_group('required arguments')
    _required_arguments.add_argument('-g', action='store', dest='game', choices={'fo4', 'tesv', 'sse'}, help='set compiler version')
    _required_arguments.add_argument('-i', action='store', dest='input', help='absolute path to input file or folder')

    _optional_arguments = _parser.add_argument_group('optional arguments')
    _optional_arguments.add_argument('--disable-anonymizer', action='store_true', default=False, help='do not anonymize script metadata')
    _optional_arguments.add_argument('--disable-bsarch', action='store_true', default=False, help='do not pack scripts with BSArch')
    _optional_arguments.add_argument('--disable-indexer', action='store_true', default=False, help='do not index scripts')

    _program_arguments = _parser.add_argument_group('program arguments')
    _program_arguments.add_argument('--help', action='store_true', dest='show_help', default=False, help='show help and exit')
    _program_arguments.add_argument('--version', action='version', version='%s' % __version__)

    _args = _parser.parse_args()

    if _args.show_help:
        exit(_parser.print_help())

    # if required arguments not set, show help
    if _args.game is None:
        log.error('required argument missing: -g {tesv,fo4,sse}' + os.linesep)
        exit(_parser.print_help())

    if _args.input is None:
        log.error('required argument missing: -i INPUT' + os.linesep)
        exit(_parser.print_help())

    if not _args.input.endswith('.ppj'):
        log.error('Single script compilation is no longer supported. Use a PPJ file.')
        exit(_parser.print_help())

    if not os.path.isabs(_args.input):
        log.warn('Relative input path detected. Using current working directory: ' + os.getcwd())
        _args.input = os.path.join(os.getcwd(), _args.input.replace('file://', ''))
        log.warn('Using input path: ' + _args.input)

    main()
