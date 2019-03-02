import configparser
import os
import sys

from GameType import GameType
from Logger import Logger
from TimeElapsed import TimeElapsed


class Project:
    """Used to pass common data to single-file and project compilation"""
    log = Logger()

    def __init__(self, game_type: GameType, input_path: str, disable_anonymizer: bool, disable_bsarch: bool, disable_indexer: bool):
        self._ini = configparser.ConfigParser()
        self._ini.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'pyro.ini'))

        self.game_type = game_type
        self.game_path = self.get_game_path()
        self.input_path = input_path
        self.disable_anonymizer = disable_anonymizer
        self.disable_bsarch = disable_bsarch
        self.disable_indexer = disable_indexer

    @property
    def is_fallout4(self):
        return self.game_type == GameType.Fallout4

    @property
    def is_skyrim_special_edition(self):
        return self.game_type == GameType.SkyrimSpecialEdition

    @property
    def is_skyrim_classic(self):
        return self.game_type == GameType.SkyrimClassic

    def _winreg_get_game_path(self) -> str:
        """Retrieve installed path of game using Windows Registry"""
        import winreg

        key_path, key_value = os.path.split(self._ini[self.game_type.name]['Registry'])

        try:
            registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
            reg_value, reg_type = winreg.QueryValueEx(registry_key, key_value)
            winreg.CloseKey(registry_key)
        except WindowsError:
            raise Exception('Game does not exist in Windows Registry. Run the game launcher once, then try again.')

        if not os.path.exists(reg_value):
            raise Exception('Directory does not exist:', reg_value)

        return reg_value

    @staticmethod
    def _handle_relative_local_path(ini_path: str, default_path: str = ''):
        """Support absolute INI paths, relative local paths, and other paths"""
        if os.path.isabs(ini_path):
            return os.path.normpath(ini_path)

        path = os.path.join(os.path.dirname(__file__), ini_path)

        if not os.path.exists(path) and default_path != '':
            path = os.path.join(default_path, ini_path)

        if not os.path.exists(path):
            raise ValueError('Path does not exist:', path)

        return os.path.normpath(path)

    @staticmethod
    def validate_script(script_path: str, time_elapsed: TimeElapsed) -> bool:
        script_path = os.path.abspath(script_path)

        if not os.path.exists(script_path):
            Project.log.pyro('ERROR: Failed to write file: {0} (file does not exist)'.format(script_path))
            return False

        if time_elapsed.start_time < os.stat(script_path).st_mtime < time_elapsed.end_time:
            Project.log.pyro('INFO: Wrote file: {0}'.format(script_path))
            return True

        Project.log.pyro('INFO: Failed to write file: {0} (not recently modified)'.format(script_path))
        return False

    def get_bsarch_path(self) -> str:
        return Project._handle_relative_local_path(self._ini['Shared']['BSArchPath'], self.game_path)

    def get_compiler_path(self) -> str:
        """Retrieve compiler path from pyro.ini"""
        return Project._handle_relative_local_path(self._ini['Compiler']['Path'], self.game_path)

    def get_flags_path(self):
        """Retrieve flags path from pyro.ini"""
        return Project._handle_relative_local_path(self._ini[self.game_type.name]['Flags'], self.game_path)

    def get_game_path(self) -> str:
        """Retrieve game path from either pyro.ini or Windows Registry"""
        game_path = self._ini['Shared']['GamePath']

        if len(game_path) > 0 and os.path.exists(game_path):
            return game_path

        if sys.platform == 'win32':
            return self._winreg_get_game_path()

        raise ValueError('Cannot retrieve game path from pyro.ini or Windows Registry')

    def get_scripts_base_path(self) -> str:
        game_path = self.get_game_path()
        return os.path.join(game_path, self._ini['Shared']['BasePath'])

    def get_scripts_source_path(self) -> str:
        game_path = self.get_game_path()
        return os.path.join(game_path, self._ini['Shared']['SourcePath'])

    def get_scripts_user_path(self) -> str:
        game_path = self.get_game_path()
        return os.path.join(game_path, self._ini['Shared']['UserPath'])
