import os
import sys

from pyro.Logger import Logger
from pyro.PathHelper import PathHelper
from pyro.ProjectOptions import ProjectOptions


class Project:
    """Used to pass common data to single-file and project compilation"""
    log = Logger()

    def __init__(self, options: ProjectOptions):
        self.options: ProjectOptions = options

    def _winreg_get_game_path(self) -> str:
        """Retrieve installed path of game using Windows Registry"""
        import winreg

        registry_type = winreg.HKEY_LOCAL_MACHINE

        if not self.options.registry_path:
            if self.options.game_type == 'fo4':
                self.options.registry_path = r'SOFTWARE\WOW6432Node\Bethesda Softworks\Fallout4\Installed Path'
            elif self.options.game_type == 'tesv':
                self.options.registry_path = r'SOFTWARE\WOW6432Node\Bethesda Softworks\Skyrim\Installed Path'
            elif self.options.game_type == 'sse':
                self.options.registry_path = r'SOFTWARE\WOW6432Node\Bethesda Softworks\Skyrim Special Edition\Installed Path'

        key_path, key_value = os.path.split(self.options.registry_path)

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

    def get_bsarch_path(self) -> str:
        # try to get bsarch path from arguments
        if self.options.bsarch_path != '':
            if os.path.isabs(self.options.bsarch_path):
                return self.options.bsarch_path
            return PathHelper.parse(self.options.bsarch_path, self.options.game_path)

        # try to get bsarch path from expected locations
        local_paths = (r'.\tools\bsarch.exe', r'..\tools\bsarch.exe')
        for path in local_paths:
            bsarch_path = os.path.realpath(os.path.join(os.path.dirname(__file__), path))
            if os.path.exists(bsarch_path):
                self.options.bsarch_path = bsarch_path
                return self.options.bsarch_path

        self.log.error('Cannot find path to BSArch.exe. Set the path or disable integration.')

    def get_compiler_path(self) -> str:
        """Retrieve compiler path from arguments"""
        return os.path.join(self.options.game_path, self.options.compiler_path)

    def get_flags_path(self) -> str:
        """Retrieve flags path from arguments"""
        if self.options.flags_path:
            return os.path.join(self.options.game_path, self.options.flags_path)

        if self.options.game_type == 'fo4':
            self.options.flags_path = os.path.join(self.options.base_path, 'Institute_Papyrus_Flags.flg')
        elif self.options.game_type == 'tesv':
            self.options.flags_path = os.path.join(self.options.source_path, 'TESV_Papyrus_Flags.flg')
        elif self.options.game_type == 'sse':
            self.options.flags_path = os.path.join(self.options.base_path, 'TESV_Papyrus_Flags.flg')

        return os.path.join(self.options.game_path, self.options.flags_path)

    def get_game_path(self) -> str:
        """Retrieve game path from arguments or Windows Registry"""
        if self.options.game_path and os.path.exists(self.options.game_path):
            return self.options.game_path

        if sys.platform == 'win32':
            self.options.game_path = self._winreg_get_game_path()
            return self.options.game_path

        if sys.platform == 'win32':
            raise ValueError('Cannot retrieve game path from arguments or Windows Registry')

        raise ValueError('Cannot retrieve game path from arguments')

    def get_scripts_base_path(self) -> str:
        return os.path.join(self.options.game_path, self.options.base_path)

    def get_scripts_source_path(self) -> str:
        return os.path.join(self.options.game_path, self.options.source_path)

    def get_scripts_user_path(self) -> str:
        return os.path.join(self.options.game_path, self.options.user_path)
