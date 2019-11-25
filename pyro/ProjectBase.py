import os
import sys

from pyro.Logger import Logger
from pyro.ProjectOptions import ProjectOptions


class ProjectBase(Logger):
    def __init__(self, options: ProjectOptions) -> None:
        self.options: ProjectOptions = options

        self.game_types: dict = {'sse': 'Skyrim Special Edition', 'tesv': 'Skyrim', 'fo4': 'Fallout 4'}

        self.program_path: str = os.path.dirname(__file__)
        if sys.argv[0].endswith(('pyro', '.exe')):
            self.program_path = os.path.abspath(os.path.join(self.program_path, os.pardir))

        self.project_name: str = os.path.splitext(os.path.basename(self.options.input_path))[0]
        self.project_path: str = os.path.dirname(self.options.input_path)

        self.import_paths: list = []

        self.optimize: bool = False
        self.release: bool = False
        self.final: bool = False

    def __setattr__(self, key: str, value: object) -> None:
        if key.endswith('path') and isinstance(value, str):
            value = os.path.normpath(value)
            if value == '.':
                value = ''
        elif key.endswith('paths') and isinstance(value, list):
            value = [os.path.normpath(path) for path in value]
        super(ProjectBase, self).__setattr__(key, value)

    # compiler arguments
    def get_compiler_path(self) -> str:
        """Returns absolute compiler path from arguments"""
        if self.options.compiler_path:
            if os.path.isabs(self.options.compiler_path):
                return self.options.compiler_path
            return os.path.join(os.getcwd(), self.options.compiler_path)
        return os.path.join(self.options.game_path, 'Papyrus Compiler', 'PapyrusCompiler.exe')

    def get_flags_path(self) -> str:
        """Returns absolute flags path or flags file name from arguments or game path"""
        if self.options.flags_path:
            if self.options.flags_path.casefold() in ('institute_papyrus_flags.flg', 'tesv_papyrus_flags.flg'):
                return self.options.flags_path
            if os.path.isabs(self.options.flags_path):
                return self.options.flags_path
            return os.path.join(self.project_path, self.options.flags_path)

        game_path: str = self.options.game_path.casefold()
        return 'Institute_Papyrus_Flags.flg' if game_path.endswith('fallout 4') else 'TESV_Papyrus_Flags.flg'

    def get_output_path(self) -> str:
        """Returns absolute output path from arguments"""
        if self.options.output_path:
            if os.path.isabs(self.options.output_path):
                return self.options.output_path
            return os.path.join(self.project_path, self.options.output_path)
        return os.path.abspath(os.path.join(self.program_path, 'out'))

    # game arguments
    def get_game_path(self, game_type: str = '') -> str:
        """Returns absolute game path from arguments or Windows Registry"""
        if self.options.game_path:
            if os.path.isabs(self.options.game_path):
                return self.options.game_path
            return os.path.join(os.getcwd(), self.options.game_path)

        if sys.platform == 'win32':
            return self.get_installed_path(game_type)

        raise FileNotFoundError('Cannot determine game path')

    def get_registry_path(self, game_type: str = '') -> str:
        if not self.options.registry_path:
            game_type = self.options.game_type if not game_type else game_type
            if game_type == 'fo4':
                return 'HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Bethesda Softworks\Fallout4\Installed Path'
            if game_type == 'tesv':
                return 'HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Bethesda Softworks\Skyrim\Installed Path'
            if game_type == 'sse':
                return 'HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Bethesda Softworks\Skyrim Special Edition\Installed Path'
            raise ValueError('Cannot determine registry path from game type')
        return self.options.registry_path.replace('/', '\\')

    def get_installed_path(self, game_type: str = '') -> str:
        """Returns absolute game path using Windows Registry"""
        import winreg

        registry_path: str = self.options.registry_path
        registry_type = winreg.HKEY_LOCAL_MACHINE

        game_type = self.options.game_type if not game_type else game_type

        if not registry_path:
            registry_path = self.get_registry_path(game_type)

        hkey, key_path = registry_path.split(os.sep, maxsplit=1)
        key_head, key_tail = os.path.split(key_path)

        # fix absolute registry paths, if needed
        if any([hkey == value for value in ('HKCU', 'HKEY_CURRENT_USER', 'HKLM', 'HKEY_LOCAL_MACHINE')]):
            if any([hkey == value for value in ('HKCU', 'HKEY_CURRENT_USER')]):
                registry_type = winreg.HKEY_CURRENT_USER

        try:
            registry_key = winreg.OpenKey(registry_type, key_head, 0, winreg.KEY_READ)
            reg_value, reg_type = winreg.QueryValueEx(registry_key, key_tail)
            winreg.CloseKey(registry_key)
        except WindowsError:
            ProjectBase.log.error('Installed Path for %s does not exist in Windows Registry. Run the game launcher once, then try again.' % self.game_types[game_type])
            sys.exit(1)

        # noinspection PyUnboundLocalVariable
        if not os.path.exists(reg_value):
            ProjectBase.log.error('Installed Path for %s does not exist: %s' % (self.game_types[game_type], reg_value))
            sys.exit(1)

        return reg_value

    # bsarch arguments
    def get_bsarch_path(self) -> str:
        """Returns absolute bsarch path from arguments"""
        if self.options.bsarch_path:
            if os.path.isabs(self.options.bsarch_path):
                return self.options.bsarch_path
            return os.path.join(os.getcwd(), self.options.bsarch_path)
        return os.path.abspath(os.path.join(self.program_path, 'tools', 'bsarch.exe'))

    def get_package_path(self) -> str:
        """Returns absolute package path from arguments"""
        if self.options.package_path:
            if os.path.isabs(self.options.package_path):
                return self.options.package_path
            return os.path.join(self.project_path, self.options.package_path)
        return os.path.abspath(os.path.join(self.program_path, 'dist'))

    def get_temp_path(self) -> str:
        """Returns absolute temp path from arguments"""
        if self.options.temp_path:
            if os.path.isabs(self.options.temp_path):
                return self.options.temp_path
            return os.path.join(os.getcwd(), self.options.temp_path)
        return os.path.abspath(os.path.join(self.program_path, 'temp'))

    # program arguments
    def get_game_type(self) -> str:
        """Returns game type from arguments or Papyrus Project"""
        if self.options.game_type:
            game_type: str = self.options.game_type.casefold()
            if game_type and game_type in self.game_types:
                return game_type

        if self.options.game_path:
            game_path = self.options.game_path.casefold()
            if game_path.endswith('skyrim special edition'):
                ProjectBase.log.warning('Using game type: Skyrim Special Edition (determined from game path)')
                return 'sse'
            if game_path.endswith('skyrim'):
                ProjectBase.log.warning('Using game type: Skyrim (determined from game path)')
                return 'tesv'
            if game_path.endswith('fallout 4'):
                ProjectBase.log.warning('Using game type: Fallout 4 (determined from game path)')
                return 'fo4'

        if self.options.registry_path:
            registry_path_parts = self.options.registry_path.casefold().split(os.sep)
            if 'skyrim special edition' in registry_path_parts:
                ProjectBase.log.warning('Using game type: Skyrim Special Edition (determined from registry path)')
                return 'sse'
            if 'skyrim' in registry_path_parts:
                ProjectBase.log.warning('Using game type: Skyrim (determined from registry path)')
                return 'tesv'
            if 'fallout 4' in registry_path_parts:
                ProjectBase.log.warning('Using game type: Fallout 4 (determined from registry path)')
                return 'fo4'

        if self.import_paths:
            for import_path in reversed(self.import_paths):
                path_parts: list = import_path.casefold().split(os.sep)
                if 'skyrim special edition' in path_parts:
                    ProjectBase.log.warning('Using game type: Skyrim Special Edition (determined from import paths)')
                    return 'sse'
                if 'skyrim' in path_parts:
                    ProjectBase.log.warning('Using game type: Skyrim (determined from import paths)')
                    return 'tesv'
                if 'fallout 4' in path_parts:
                    ProjectBase.log.warning('Using game type: Fallout 4 (determined from import paths)')
                    return 'fo4'

        if self.options.flags_path:
            flags_path: str = self.options.flags_path.casefold()
            if flags_path.endswith('institute_papyrus_flags.flg'):
                ProjectBase.log.warning('Using game type: Fallout 4 (determined from flags path)')
                return 'fo4'
            if flags_path.endswith('tesv_papyrus_flags.flg'):
                try:
                    self.get_game_path('sse')
                    ProjectBase.log.warning('Using game type: Skyrim Special Edition (determined from flags path)')
                    return 'sse'
                except FileNotFoundError:
                    ProjectBase.log.warning('Using game type: Skyrim (determined from flags path)')
                    return 'tesv'

        return ''

    def get_log_path(self) -> str:
        """Returns absolute log path from arguments"""
        if self.options.log_path:
            if os.path.isabs(self.options.log_path):
                return self.options.log_path
            return os.path.join(os.getcwd(), self.options.log_path)
        return os.path.abspath(os.path.join(self.program_path, 'logs'))
