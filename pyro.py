# coding=utf-8

from __future__ import print_function

import argparse
import os
import platform
import subprocess
import time
import sys

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


__version__ = 'pyro-1.2 by fireundubh <github.com/fireundubh>'

PROGRAM_PATH = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

SOURCE_PATH = os.path.join('Data', 'Scripts', 'Source')
BASE_PATH = os.path.join(SOURCE_PATH, 'Base')
USER_PATH = os.path.join(SOURCE_PATH, 'User')
FILE_EXTENSIONS = ['.psc', '.pex']

XML_PARSER = etree.XMLParser(remove_blank_text=True)


def main():
    """Determine arguments and pass arguments to compiler"""
    compile_project = True

    is_file = os.path.isfile(args.input)
    is_folder = os.path.isdir(args.input)

    if is_file:
        file_extension = os.path.splitext(args.input)[1]
        if file_extension == '.psc':
            if args.game == 'fo4':
                compiler_args.append('-release')
                compiler_args.append('-final')
            compile_project = False
    elif is_folder:
        compiler_args.append('-all')
        compile_project = False

    if not args.skip_output_validation or args.show_time_elapsed:
        start_time = time.time()

    if not compile_project:
        capture(subprocess.Popen(compiler_args, stdout=subprocess.PIPE, shell=False, universal_newlines=True))
    else:
        if args.game == 'fo4':
            project_args = [compiler_path, args.input]
            project_args.append('-q') if args.quiet else None
            capture(subprocess.Popen(project_args, stdout=subprocess.PIPE, shell=False, universal_newlines=True))
        else:
            xml_process_ppj(args.input)

    if not args.skip_output_validation or args.show_time_elapsed:
        end_time = time.time()

    if not args.skip_output_validation:
        if not compile_project:
            output_file = os.path.basename(args.input)
            if args.game == 'fo4' and os.path.join('Source', 'User').lower() in args.input.lower():
                output_file = os.path.join(*args.input.split('\\')[-2:])
            # noinspection PyUnboundLocalVariable
            validate_output(os.path.join(args.output, output_file.replace(*FILE_EXTENSIONS)), start_time, end_time)
        else:
            output_path = xml_get_output(args.input)
            scripts = [os.path.join(output_path, script.replace(*FILE_EXTENSIONS)) for script in xml_get_scripts(args.input)]
            if args.game != 'fo4':
                scripts = [os.path.join(output_path, os.path.basename(script)) for script in scripts]
            for script in scripts:
                # noinspection PyUnboundLocalVariable
                validate_output(script, start_time, end_time)

    if args.show_time_elapsed:
        # noinspection PyUnboundLocalVariable
        print('[PYRO] Time elapsed: ' + '{0:.2f}s'.format(float(end_time - start_time)))


def validate_output(script, start_time, end_time):
    if os.path.exists(script):
        if start_time < os.stat(script).st_mtime < end_time:
            print('[PYRO] Wrote file: ' + script)
        else:
            print('[PYRO] Failed to write file: ' + script + ' (not recently modified)')
    else:
        print('[PYRO] Failed to write file: ' + script + ' (file does not exist)')


def xml_get_scripts(input_file):
    """Returns a list of scripts in XML file"""
    root = etree.parse(input_file, XML_PARSER).getroot()
    return xml_get_child_node_values(root, 'Scripts')


def xml_get_output(input_file):
    """Returns the output path in XML file"""
    root = etree.parse(input_file, XML_PARSER).getroot()
    return str(root.get('Output'))


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

    generated_imports = generate_imports_from_scripts(script_paths, import_paths)

    commands = []
    for script_path in script_paths:
        params = [script_path, optimize, output_path, generated_imports, flags]
        cmd = build_arguments_as_string(*params)
        commands.append(cmd)

    process_queue = [subprocess.Popen(cmd, shell=False, universal_newlines=True) for cmd in commands]
    for process in process_queue:
        process.wait()


def xml_get_bool_attr(root, attr):
    """Returns boolean value of attribute or False if attribute does not exist"""
    if attr not in root.attrib:
        return False
    return bool(root.get(attr))


def xml_get_child_node_values(root, tag, namespace='PapyrusProject.xsd'):
    """Return list of child node text values using namespace"""
    parent = root.find('ns:%s' % tag, {'ns': '%s' % namespace})
    if parent is None:
        return None

    children = parent.findall('ns:%s' % tag[:-1], {'ns': '%s' % namespace})
    if len(children) == 0 or children is None:
        return None

    return xml_get_field_text(children)


def xml_validate_flags(root):
    """Validate and return flags attribute value from XML"""
    result = os.path.basename(get_flags_path(args.game))
    if 'Flags' in root.attrib:
        xml_result = root.get('Flags')
        if result != xml_result:
            raise ValueError('Cannot proceed without correct flags for game: %s' % xml_result)
        return xml_result
    return result


def build_arguments_as_string(script_path, optimize, output_path, import_paths, flags):
    """Generate string of arguments for compiler"""
    result = ['"%s"' % compiler_path, '"%s"' % script_path, '-o="%s"' % output_path, '-i="%s"' % ';'.join(import_paths), '-f="%s"' % flags]
    if optimize:
        result.insert(2, '-op')
    if args.quiet:
        result.append('-q')
    return ' '.join(result)


def remove_duplicates_in_list(items):
    """Removes duplicate items in list and returns list"""
    for item in items:
        while items.count(item) > 1:
            items.remove(item)
    return items


def generate_imports_from_scripts(scripts, import_paths):
    """Generate list of unique paths to scripts from imports"""
    if import_paths is None:
        import_paths = [import_path for import_path in default_imports if os.path.exists(import_path)]

    script_bases = [os.path.join(import_path, os.path.dirname(script)) for import_path in import_paths for script in scripts]
    script_bases = [script_base for script_base in script_bases if os.path.exists(script_base)]

    import_paths = remove_duplicates_in_list(import_paths)
    script_bases = remove_duplicates_in_list(script_bases)

    return list(script_bases + import_paths)


def xml_get_field_text(fields):
    """Returns list of field values from fields"""
    return [str(field.text) for field in fields if field.text is not None and field.text != '']


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
        raise Exception('File does not exist: ' + result)

    return result


def get_user_path(game):
    """Retrieve path to user scripts folder"""
    result = os.path.join(game_path, USER_PATH) if game in ['fo4', 'sse'] else os.path.join(game_path, SOURCE_PATH)
    if not os.path.exists(result):
        raise Exception('Directory does not exist: ' + result)
    return result


def get_game_scripts_path(game):
    """Retrieve path to game scripts folder"""
    result = os.path.join(game_path, BASE_PATH) if game in ['fo4', 'sse'] else os.path.join(game_path, SOURCE_PATH)
    if not os.path.exists(result):
        raise Exception('Directory does not exist: ' + result)
    return result


def get_registry_value(reg_path, key):
    """Retrieve key value from Windows Registry"""
    registry_key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, reg_path, 0, _winreg.KEY_READ)
    value, regtype = _winreg.QueryValueEx(registry_key, key)
    _winreg.CloseKey(registry_key)
    return value


def get_script_folder():
    result = os.path.dirname(args.input)
    if os.path.join('Source', 'User').lower() in result.lower():
        result = os.path.dirname(result)
    return result


def get_compiler_path():
    result = os.path.join(game_path, os.path.join('Papyrus Compiler', 'PapyrusCompiler.exe'))
    if not os.path.exists(result):
        raise Exception('Compiler does not exist at path: ' + result)
    return result


def capture(output):
    """Prints stdout messages in real time without extra line breaks"""
    while True:
        state = output.poll()
        if state is not None and state >= 0:
            exit(state)
        line = output.stdout.readline().strip()
        if not line or line == '':
            break
        result = '[COMPILER] ' + line
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
    optional_arguments.add_argument('-q', action='store_true', dest='quiet', default=False, help='report only compiler failures')
    optional_arguments.add_argument('-s', action='store_true', dest='skip_output_validation', default=False, help='skip output validation')
    optional_arguments.add_argument('-t', action='store_true', dest='show_time_elapsed', default=False, help='show time elapsed during compilation')

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

    # global variables
    game_path = get_game_path(args.game)
    compiler_path = get_compiler_path()
    flags_path = get_flags_path(args.game)
    user_path = get_user_path(args.game)
    script_folder = get_script_folder()
    game_scripts_path = get_game_scripts_path(args.game)
    default_imports = [script_folder, user_path, game_scripts_path]

    # output parser
    relative_base_path = os.path.dirname(args.input)
    if args.output == '..':
        project_output_path = [relative_base_path, os.pardir]
        if os.path.join('Source', 'User').lower() in args.output.lower():
            project_output_path = project_output_path + [os.pardir, os.pardir]
        if project_output_path is not None:
            args.output = os.path.abspath(os.path.join(*project_output_path))

    elif args.output == '.':
        args.output = os.path.abspath(os.path.join(relative_base_path, os.curdir))

    elif not os.path.isabs(args.output):
        raise ValueError('Cannot proceed with relative output path: ' + args.output)

    compiler_args = [
        '%s' % compiler_path,
        '%s' % args.input,
        '-op',
        '-o=%s' % args.output,
        '-i=%s' % ';'.join(default_imports),
        '-f=%s' % flags_path
    ]

    print(compiler_args)

    if args.quiet:
        compiler_args.append('-q')

    main()
