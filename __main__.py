import argparse
import os

from CLI import CLI
from Logger import Logger

__version__ = 'pyro-1.3.1 by fireundubh <github.com/fireundubh>'

if __name__ == '__main__':
    logger = Logger()

    if not os.path.exists(os.path.join(os.path.dirname(__file__), 'pyro.ini')):
        exit(logger.error('Cannot proceed without pyro.ini configuration file'))

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

    CLI.run(_parser, logger)
