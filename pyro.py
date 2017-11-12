# coding=utf-8

from __future__ import print_function

import sys

import argparse
import os
import platform
import subprocess
import traceback

if sys.version_info < (3, 0):
    # noinspection PyUnresolvedReferences
    import _winreg
else:
    import winreg as _winreg

try:
    from lxml import etree
except ImportError:
    subprocess.call([sys.executable, '-m', 'pip', 'install', 'lxml'])
    # noinspection PyUnresolvedReferences
    from lxml import etree

__version__ = 'pyro-1.0 by fireundubh <github.com/fireundubh>'

PROGRAM_PATH = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

SOURCE_PATH = os.path.join('Data', 'Scripts', 'Source')
BASE_PATH = os.path.join(SOURCE_PATH, 'Base')
USER_PATH = os.path.join(SOURCE_PATH, 'User')

XML_PARSER = etree.XMLParser(remove_blank_text=True)


def main():
    """Determine arguments and pass arguments to compiler"""
    compile_scripts = False
    compile_project = False

    is_file = os.path.isfile(args.input)
    is_folder = os.path.isdir(args.input)

    if is_file:
        file_extension = os.path.splitext(args.input)[1]
        if file_extension == '.psc':
            if args.game == 'fo4':
                compiler_args.append('-release')
                compiler_args.append('-final')
            compile_scripts = True
        elif file_extension == '.ppj':
            compile_project = True
    elif is_folder:
        compiler_args.append('-all')
        compile_scripts = True

    if compile_scripts:
        capture(subprocess.Popen(compiler_args, stdout=subprocess.PIPE, shell=False, universal_newlines=True))
    elif compile_project:
        if args.game == 'fo4':
            capture(subprocess.Popen([compiler_args[0], compiler_args[1]], stdout=subprocess.PIPE, shell=False, universal_newlines=True))
        else:
            xml_process_ppj(args.input)


def xml_process_ppj(input_file):
    """Compile project scripts in parallel"""
    root = etree.parse(input_file, XML_PARSER).getroot()

    # root attributes
    optimize = xml_get_bool_attr(root, 'Optimize')
    output_path = args.output if 'Output' not in root.attrib else root.get('Output')
    flags = xml_validate_flags(root)

    # script and import paths
    script_paths = xml_get_child_node_values(root, 'Scripts')
    import_paths = xml_get_child_node_values(root, 'Imports')
    imports = build_imports_from_scripts(script_paths, import_paths) + import_paths

    # compile scripts in parallel
    queue = []
    for script_path in script_paths:
        arg_string = build_arguments_as_string(script_path, optimize, output_path, imports, flags)
        output = subprocess.Popen(arg_string, stderr=subprocess.STDOUT, shell=False, universal_newlines=True)
        queue.append(output)

    for q in queue:
        q.wait()


def xml_get_bool_attr(root, attr):
    """Returns boolean value of attribute or False if attribute does not exist"""
    if attr not in root.attrib:
        return False
    return bool(root.get(attr))


def xml_get_child_node_values(root, tag):
    """Return list of child node text values using namespace"""
    ns = {'ns': 'PapyrusProject.xsd'}

    parent = root.find('ns:%s' % tag, ns)
    if parent is None:
        raise SyntaxError('Cannot proceed without required node: <%s>' % tag)

    children = parent.findall('ns:%s' % tag[:-1], ns)
    if len(children) == 0 or children is None:
        raise SyntaxError('Cannot proceed without required nodes: <%s>' % tag[:-1])

    return xml_get_field_text(children)


def xml_validate_flags(root):
    """Validate and return flags attribute value from XML"""
    flags = os.path.basename(get_flags_path(args.game))
    if 'Flags' in root.attrib:
        flags_attr = root.get('Flags')
        if flags != flags_attr:
            raise ValueError('Cannot proceed without correct flags for game: %s' % flags_attr)
        return flags_attr
    return flags


def build_arguments_as_string(script_path, optimize, output_path, imports, flags):
    """Generate string of arguments for compiler"""
    result = ['"%s"' % compiler_path, '"%s"' % script_path, '-o="%s"' % output_path, '-i="%s"' % ';'.join(imports), '-f="%s"' % flags]
    if optimize:
        result.insert(2, '-op')
    return ' '.join([str(x) for x in result])


def build_imports_from_scripts(scripts, imports):
    """Generate list of unique paths to scripts from imports"""
    script_bases = list()
    for script in scripts:
        for import_path in imports:
            script_base = os.path.join(import_path, os.path.dirname(script))
            if os.path.exists(script_base):
                script_bases.append(script_base)
                break
    return list(set(script_bases))


def xml_get_field_text(fields):
    """Append field text to files list"""
    files = list()
    for field in fields:
        files.append(field.text)
    return files


def get_game_path(game):
    """Retrieve installed path of game using Windows Registry"""
    if game == 'fo4':
        key_path = r'SOFTWARE\WOW6432Node\Bethesda Softworks\Fallout4'
    elif game == 'sse':
        key_path = r'SOFTWARE\WOW6432Node\Bethesda Softworks\Skyrim Special Edition'
    else:
        key_path = r'SOFTWARE\WOW6432Node\Bethesda Softworks\Skyrim'

    try:
        result = get_registry_value(key_path, 'Installed Path')
    except WindowsError:
        raise Exception('Game does not exist in Windows Registry. Run the game launcher once, then try again.')

    if not os.path.exists(result):
        raise Exception('Directory does not exist: %s' % result)

    return result


def get_flags_path(game):
    """Retrieve path to compiler flags"""
    if game == 'fo4':
        result = os.path.join(game_path, BASE_PATH, 'Institute_Papyrus_Flags.flg')
    elif game == 'sse':
        result = os.path.join(game_path, BASE_PATH, 'TESV_Papyrus_Flags.flg')
    else:
        result = os.path.join(game_path, SOURCE_PATH, 'TESV_Papyrus_Flags.flg')

    if not os.path.exists(result):
        raise Exception('File does not exist: %s' % result)

    return result


def get_user_path(game):
    """Retrieve path to user scripts folder"""
    if game in ['fo4', 'sse']:
        result = os.path.join(game_path, USER_PATH)
    else:
        result = os.path.join(game_path, SOURCE_PATH)

    if not os.path.exists(result):
        raise Exception('Directory does not exist: %s' % result)

    return result

def get_game_scripts_path(game):
    """Retrieve path to game scripts folder"""
    if game in ['fo4', 'sse']:
        result = os.path.join(game_path, BASE_PATH)
    else:
        result = os.path.join(game_path, SOURCE_PATH)

    if not os.path.exists(result):
        raise Exception('Directory does not exist: %s' % result)

    return result


def get_registry_value(reg_path, key):
    """Retrieve key value from Windows Registry"""
    try:
        registry_key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, reg_path, 0, _winreg.KEY_READ)
        value, regtype = _winreg.QueryValueEx(registry_key, key)
        _winreg.CloseKey(registry_key)
        return value
    except WindowsError:
        traceback.print_exc()


def get_script_folder():
    result = os.path.dirname(args.input)
    if r'source\User' in result:
        result = os.path.dirname(result)
    return result


def get_compiler_path():
    result = os.path.join(game_path, os.path.join('Papyrus Compiler', 'PapyrusCompiler.exe'))
    if not os.path.exists(result):
        raise Exception('Compiler does not exist at path: %s' % result)
    return result


def capture(output):
    """Prints stdout messages in real time without extra line breaks"""
    while True:
        line = output.stdout.readline()
        if not line:
            break
        result = line.strip()
        print(result)


if __name__ == '__main__':
    if platform.system() != 'Windows':
        raise OSError('Cannot run on non-Windows platform due to use of Windows Registry to determine paths')

    parser = argparse.ArgumentParser(add_help=False)

    required_arguments = parser.add_argument_group('required arguments')
    required_arguments.add_argument('-g', action='store', dest='game', choices={'fo4', 'sse', 'tesv'}, help='set compiler version')
    required_arguments.add_argument('-i', action='store', dest='input', help='set absolute path to input file or folder')

    optional_arguments = parser.add_argument_group('optional arguments')
    optional_arguments.add_argument('-o', action='store', dest='output', default='..', help='set absolute path to output folder (default: ..)')

    optional_flags = parser.add_argument_group('optional flags')
    optional_flags.add_argument('-p', action='store_true', dest='project_output', default=False, help='resolve .. to compiled project scripts folder')

    program_arguments = parser.add_argument_group('program arguments')
    program_arguments.add_argument('--help', action='store_true', dest='show_help', default=False, help='show help and exit')
    program_arguments.add_argument('--version', action='version', version='%s' % __version__)

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

    # more information
    if args.project_output and args.output not in ['.', '..']:
        print('[WARN] given argument not applicable, skipping: -p' + os.linesep)

    game_path = get_game_path(args.game)
    flags_path = get_flags_path(args.game)

    compiler_path = get_compiler_path()

    game_scripts_path = get_game_scripts_path(args.game)
    user_path = get_user_path(args.game)

    script_folder = get_script_folder()

    default_imports = [script_folder, user_path, game_scripts_path]

    # output parser
    relative_base_path = os.path.dirname(args.input)
    if args.output == '..':
        args.output = os.path.join(relative_base_path, os.pardir)
        if args.project_output:
            args.output = os.path.join(relative_base_path, os.pardir, os.pardir, os.pardir)
    elif args.output == '.':
        args.output = os.path.join(relative_base_path, os.curdir)
    elif not os.path.isabs(args.output):
        raise ValueError('Cannot proceed with relative output path: %s' % args.output)

    compiler_args = [
        '%s' % compiler_path,
        '%s' % args.input,
        '-op',
        '-o=%s' % args.output,
        '-i=%s' % ';'.join(default_imports),
        '-f=%s' % flags_path
    ]

    main()
