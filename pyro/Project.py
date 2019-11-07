import configparser
import os
import sys

from pyro.Logger import Logger
from pyro.PathHelper import PathHelper
from pyro.ProjectOptions import ProjectOptions
from pyro.TimeElapsed import TimeElapsed
from pyro.enums import GameType, ValidationState


class Project:
    """Used to pass common data to single-file and project compilation"""
    log = Logger()

    def __init__(self, options: ProjectOptions):
        self._ini: configparser.ConfigParser = configparser.ConfigParser()
        self._ini.read(options.pyro_cfg_path)
        self.game_path = None

        self.options: ProjectOptions = options

    @property
    def is_fallout4(self) -> bool:
        return self.options.game_type == GameType.Fallout4

    @property
    def is_skyrim_special_edition(self) -> bool:
        return self.options.game_type == GameType.SkyrimSpecialEdition

    @property
    def is_skyrim_classic(self) -> bool:
        return self.options.game_type == GameType.SkyrimClassic

    def _winreg_get_game_path(self) -> str:
        """Retrieve installed path of game using Windows Registry"""
        import winreg

        game_type = self.options.game_type
        key_path, key_value = os.path.split(self._ini[game_type.name]['Registry'])

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
    def validate_script(script_path: str, time_elapsed: TimeElapsed) -> ValidationState:
        script_path = os.path.abspath(script_path)

        if not os.path.exists(script_path):
            Project.log.pyro('ERROR: Failed to write file: {0} (file does not exist)'.format(script_path))
            return ValidationState.FILE_NOT_EXIST

        if time_elapsed.start_time < os.stat(script_path).st_mtime < time_elapsed.end_time:
            Project.log.pyro('INFO: Wrote file: {0}'.format(script_path))
            return ValidationState.FILE_MODIFIED

        Project.log.pyro('INFO: Skipped writing file: {0} (not recently modified)'.format(script_path))
        return ValidationState.FILE_NOT_MODIFIED

    def get_bsarch_path(self) -> str:
        return PathHelper.parse(self._ini['Pyro']['BSArchPath'], self.get_game_path())

    def get_compiler_path(self) -> str:
        """Retrieve compiler path from pyro.ini"""
        return PathHelper.parse(self._ini['Compiler']['Path'], self.get_game_path())

    def get_flags_path(self) -> str:
        """Retrieve flags path from pyro.ini"""
        return PathHelper.parse(self._ini[self.options.game_type.name]['Flags'], self.get_game_path())

    def get_game_path(self) -> str:
        """Retrieve game path from either pyro.ini or Windows Registry"""
        if self.game_path:
            return self.game_path
        game_path = self._ini['Shared']['GamePath']

        if len(game_path) > 0 and os.path.exists(game_path):
            self.game_path = game_path
            return game_path

        if sys.platform == 'win32':
            game_path = self._winreg_get_game_path()
            self.game_path = game_path
            return game_path

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
