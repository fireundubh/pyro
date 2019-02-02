import configparser
import os
import sys

from GameType import GameType


class Project:
    """Used to pass common data to single-file and project compilation"""
    USER_PATH_PART = os.path.join('Source', 'User').casefold()

    def __init__(self, game_type: GameType, input_path: str, output_path: str):
        self._ini = configparser.ConfigParser()
        self._ini.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'pyro.ini'))

        self.game_type = game_type
        self.game_path = self.get_game_path()
        self.input_path = input_path
        self.output_path = output_path

    @property
    def compiler_path(self) -> str:
        """Retrieve compiler path from pyro.ini"""
        return os.path.join(self.game_path, self._ini['Compiler']['Path'])

    @property
    def flags_path(self):
        """Retrieve flags path from pyro.ini"""
        return os.path.join(self.game_path, self._ini[self.game_type.name]['Flags'])

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

    def get_game_path(self) -> str:
        """Retrieve game path from either pyro.ini or Windows Registry"""
        game_path = self._ini['Shared']['GamePath']

        if len(game_path) > 0 and os.path.exists(game_path):
            return game_path

        if sys.platform == 'win32':
            return self._winreg_get_game_path()

        raise ValueError('Cannot retrieve game path from pyro.ini or Windows Registry')

    def try_parse_relative_output_path(self) -> str:
        """Try to parse the user-defined relative project output path. If the path is not relative, return the unmodified path."""
        relative_base_path = os.path.dirname(self.input_path)

        if self.output_path == '..':
            project_output_path = [relative_base_path, os.pardir]

            if Project.USER_PATH_PART in self.output_path.casefold():
                project_output_path = project_output_path + [os.pardir, os.pardir]

            if project_output_path is not None:
                return os.path.abspath(os.path.join(*project_output_path))

            return self.output_path

        if self.output_path == '.':
            return os.path.abspath(os.path.join(relative_base_path, os.curdir))

        if not os.path.isabs(self.output_path):
            raise ValueError('Cannot proceed with relative output path:', self.output_path)

        return self.output_path
