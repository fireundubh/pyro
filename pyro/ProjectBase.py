import os
import sys

from pyro.Logger import Logger
from pyro.ProjectOptions import ProjectOptions


class ProjectBase:
    log = Logger()

    def __init__(self, options: ProjectOptions) -> None:
        self.options: ProjectOptions = options
        self.program_path: str = os.path.dirname(__file__)

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
            return os.path.join(os.getcwd(), self.options.flags_path)

        game_path: str = self.options.game_path.casefold()
        return 'Institute_Papyrus_Flags.flg' if game_path.endswith('fallout 4') else 'TESV_Papyrus_Flags.flg'

    def get_output_path(self) -> str:
        """Returns absolute output path from arguments"""
        if not self.options.output_path:
            if os.path.abspath(self.options.output_path):
                return self.options.output_path
            return os.path.join(os.getcwd(), self.options.output_path)
        return os.path.realpath(os.path.join(self.program_path, os.pardir, 'out'))

    # game arguments
    def get_game_path(self) -> str:
        """Returns absolute game path from arguments or Windows Registry"""
        if self.options.game_path:
            if os.path.isabs(self.options.game_path):
                return self.options.game_path
            return os.path.join(os.getcwd(), self.options.game_path)

        if sys.platform == 'win32':
            return self.get_registry_path()

        return ''

    def get_registry_path(self) -> str:
        """Returns absolute game path using Windows Registry"""
        import winreg

        registry_path = self.options.registry_path
        registry_type = winreg.HKEY_LOCAL_MACHINE

        if not registry_path:
            if self.options.game_type == 'fo4':
                registry_path = r'SOFTWARE\WOW6432Node\Bethesda Softworks\Fallout4\Installed Path'
            elif self.options.game_type == 'tesv':
                registry_path = r'SOFTWARE\WOW6432Node\Bethesda Softworks\Skyrim\Installed Path'
            elif self.options.game_type == 'sse':
                registry_path = r'SOFTWARE\WOW6432Node\Bethesda Softworks\Skyrim Special Edition\Installed Path'

        key_path, key_value = os.path.split(registry_path)

        # fix absolute registry paths, if needed
        key_parts = key_path.split(os.sep)
        if key_parts[0] in ('HKCU', 'HKEY_CURRENT_USER', 'HKLM', 'HKEY_LOCAL_MACHINE'):
            if key_parts[0] in ('HKCU', 'HKEY_CURRENT_USER'):
                registry_type = winreg.HKEY_CURRENT_USER
            key_path = os.sep.join(key_parts[1:])

        try:
            registry_key = winreg.OpenKey(registry_type, key_path, 0, winreg.KEY_READ)
            reg_value, reg_type = winreg.QueryValueEx(registry_key, key_value)
            winreg.CloseKey(registry_key)
        except WindowsError:
            sys.exit(self.log.error('Game does not exist in Windows Registry. Run the game launcher once, then try again.'))

        # noinspection PyUnboundLocalVariable
        if not os.path.exists(reg_value):
            sys.exit(self.log.error('Directory does not exist: %s' % reg_value))

        return reg_value

    # bsarch arguments
    def get_bsarch_path(self) -> str:
        """Returns absolute bsarch path from arguments"""
        if self.options.bsarch_path:
            if os.path.isabs(self.options.bsarch_path):
                return self.options.bsarch_path
            return os.path.join(os.getcwd(), self.options.bsarch_path)
        return os.path.realpath(os.path.join(self.program_path, 'tools', 'bsarch.exe'))

    def get_archive_path(self) -> str:
        """Returns absolute archive path from arguments"""
        if self.options.archive_path:
            if os.path.isabs(self.options.archive_path):
                return self.options.archive_path
            return os.path.join(os.getcwd(), self.options.archive_path)
        return os.path.realpath(os.path.join(self.program_path, os.pardir, 'dist'))

    def get_temp_path(self) -> str:
        """Returns absolute temp path from arguments"""
        if self.options.temp_path:
            if os.path.isabs(self.options.temp_path):
                return self.options.temp_path
            return os.path.join(os.getcwd(), self.options.temp_path)
        return os.path.realpath(os.path.join(self.program_path, os.pardir, 'temp'))

    # program arguments
    def get_log_path(self) -> str:
        """Returns absolute log path from arguments"""
        if self.options.log_path:
            if os.path.isabs(self.options.log_path):
                return self.options.log_path
            return os.path.join(os.getcwd(), self.options.log_path)
        return os.path.realpath(os.path.join(self.program_path, os.pardir, 'logs'))
