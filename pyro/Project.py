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

        registry_path = getattr(self.options, '%s_registry_path' % self.options.game_type)
        key_path, key_value = os.path.split(registry_path)

        try:
            registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
            reg_value, reg_type = winreg.QueryValueEx(registry_key, key_value)
            winreg.CloseKey(registry_key)
        except WindowsError:
            raise Exception('Game does not exist in Windows Registry. Run the game launcher once, then try again.')

        if not os.path.exists(reg_value):
            raise Exception('Directory does not exist:', reg_value)

        return reg_value

    def get_bsarch_path(self) -> str:
        return PathHelper.parse(self.options.bsarch_path, self.get_game_path())

    def get_compiler_path(self) -> str:
        """Retrieve compiler path from arguments"""
        return os.path.join(self.get_game_path(), self.options.compiler_path)

    def get_flags_path(self) -> str:
        """Retrieve flags path from arguments"""
        flags_path: str = getattr(self.options, '%s_flags_path' % self.options.game_type)
        return os.path.join(self.get_game_path(), flags_path)

    def get_game_path(self) -> str:
        """Retrieve game path from arguments or Windows Registry"""
        if len(self.options.game_path) > 0 and os.path.exists(self.options.game_path):
            return self.options.game_path

        if sys.platform == 'win32':
            self.options.game_path = self._winreg_get_game_path()
            return self.options.game_path

        if sys.platform == 'win32':
            raise ValueError('Cannot retrieve game path from arguments or Windows Registry')

        raise ValueError('Cannot retrieve game path from arguments')

    def get_scripts_base_path(self) -> str:
        game_path = self.get_game_path()
        return os.path.join(game_path, self.options.base_path)

    def get_scripts_source_path(self) -> str:
        game_path = self.get_game_path()
        return os.path.join(game_path, self.options.source_path)

    def get_scripts_user_path(self) -> str:
        game_path = self.get_game_path()
        return os.path.join(game_path, self.options.user_path)
