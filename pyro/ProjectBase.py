import logging
import os
import sys
from typing import List, Union

from pyro.ProjectOptions import ProjectOptions
from pyro.StringTemplate import StringTemplate


class ProjectBase:
    log: logging.Logger = logging.getLogger('pyro')

    options: ProjectOptions = None

    game_types: dict = {'sse': 'Skyrim Special Edition', 'tesv': 'Skyrim', 'fo4': 'Fallout 4'}
    variables: dict = {}

    program_path: str = ''
    project_name: str = ''
    project_path: str = ''

    import_paths: list = []

    final: bool = False
    optimize: bool = False
    release: bool = False

    def __init__(self, options: ProjectOptions) -> None:
        self.options = options

        self.program_path = os.path.dirname(__file__)
        if sys.argv[0].endswith(('pyro', '.exe')):
            self.program_path = os.path.abspath(os.path.join(self.program_path, os.pardir))

        self.project_name = os.path.splitext(os.path.basename(self.options.input_path))[0]
        self.project_path = os.path.dirname(self.options.input_path)

    def __setattr__(self, key: str, value: object) -> None:
        if isinstance(value, str) and key.endswith('path'):
            if value != os.curdir:
                value = os.path.normpath(value)
                if value == os.curdir:
                    value = ''
        elif isinstance(value, list) and key.endswith('paths'):
            value = [os.path.normpath(path) if path != os.curdir else path for path in value]
        super(ProjectBase, self).__setattr__(key, value)

    @staticmethod
    def _get_path(path: str, *, relative_root_path: str, fallback_path: Union[str, List]) -> str:
        """
        Returns absolute path from path or fallback path if path empty or unset

        :param path: A relative or absolute path
        :param relative_root_path: Absolute path to directory to join with relative path
        :param fallback_path: Absolute path to return if path empty or unset
        """
        if path:
            return path if os.path.isabs(path) else os.path.join(relative_root_path, path)
        if isinstance(fallback_path, list):
            return os.path.abspath(os.path.join(*fallback_path))
        return fallback_path

    def parse(self, value: str) -> str:
        t = StringTemplate(value)
        try:
            return os.path.expanduser(os.path.expandvars(t.substitute(self.variables)))
        except KeyError as e:
            ProjectBase.log.error(f'Failed to parse variable "{e.args[0]}" in "{value}". Is the variable name correct?')
            sys.exit(1)

    # build arguments
    def get_worker_limit(self) -> int:
        """Returns worker limit from arguments"""
        if self.options.worker_limit > 0:
            return self.options.worker_limit
        try:
            cpu_count = os.cpu_count()  # can be None if indeterminate
            if cpu_count is None:
                raise ValueError('The number of CPUs in the system is indeterminate')
        except (NotImplementedError, ValueError):
            return 2
        else:
            return cpu_count

    # compiler arguments
    def get_compiler_path(self) -> str:
        """Returns absolute compiler path from arguments"""
        return self._get_path(self.options.compiler_path,
                              relative_root_path=os.getcwd(),
                              fallback_path=[self.options.game_path, 'Papyrus Compiler', 'PapyrusCompiler.exe'])

    def get_flags_path(self) -> str:
        """Returns absolute flags path or flags file name from arguments or game path"""
        if self.options.flags_path:
            if self.options.flags_path.casefold() in ('institute_papyrus_flags.flg', 'tesv_papyrus_flags.flg'):
                return self.options.flags_path
            if os.path.isabs(self.options.flags_path):
                return self.options.flags_path
            return os.path.join(self.project_path, self.options.flags_path)

        game_path = self.options.game_path.casefold()
        return 'Institute_Papyrus_Flags.flg' if game_path.endswith('fallout 4') else 'TESV_Papyrus_Flags.flg'

    def get_output_path(self) -> str:
        """Returns absolute output path from arguments"""
        return self._get_path(self.options.output_path,
                              relative_root_path=self.project_path,
                              fallback_path=[self.program_path, 'out'])

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
                game_name = 'Fallout4'
            elif game_type == 'sse':
                game_name = 'Skyrim Special Edition'
            elif game_type == 'tesv':
                game_name = 'Skyrim'
            else:
                raise ValueError('Cannot determine registry path from game type')
            return rf'HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Bethesda Softworks\\{game_name}\Installed Path'
        return self.options.registry_path.replace('/', '\\')

    def get_installed_path(self, game_type: str = '') -> str:
        """Returns absolute game path using Windows Registry"""
        import winreg

        registry_path = self.options.registry_path
        registry_type = winreg.HKEY_LOCAL_MACHINE

        game_type = self.options.game_type if not game_type else game_type

        if not registry_path:
            registry_path = self.get_registry_path(game_type)

        hkey, key_path = registry_path.split(os.sep, maxsplit=1)
        key_head, key_tail = os.path.split(key_path)

        # fix absolute registry paths, if needed
        if any([hkey == value for value in ('HKCU', 'HKEY_CURRENT_USER')]):
            registry_type = winreg.HKEY_CURRENT_USER

        try:
            registry_key = winreg.OpenKey(registry_type, key_head, 0, winreg.KEY_READ)
            reg_value, _ = winreg.QueryValueEx(registry_key, key_tail)
            winreg.CloseKey(registry_key)
        except WindowsError:
            ProjectBase.log.error(f'Installed Path for {self.game_types[game_type]} '
                                  f'does not exist in Windows Registry. Run the game launcher once, then try again.')
            sys.exit(1)

        # noinspection PyUnboundLocalVariable
        if not os.path.exists(reg_value):
            ProjectBase.log.error(f'Installed Path for {self.game_types[game_type]} does not exist: {reg_value}')
            sys.exit(1)

        return reg_value

    # bsarch arguments
    def get_bsarch_path(self) -> str:
        """Returns absolute bsarch path from arguments"""
        return self._get_path(self.options.bsarch_path,
                              relative_root_path=os.getcwd(),
                              fallback_path=[self.program_path, 'tools', 'bsarch.exe'])

    def get_package_path(self) -> str:
        """Returns absolute package path from arguments"""
        return self._get_path(self.options.package_path,
                              relative_root_path=self.project_path,
                              fallback_path=[self.program_path, 'dist'])

    def get_temp_path(self) -> str:
        """Returns absolute package temp path from arguments"""
        return self._get_path(self.options.temp_path,
                              relative_root_path=os.getcwd(),
                              fallback_path=[self.program_path, 'temp'])

    # zip arguments
    def get_zip_output_path(self) -> str:
        """Returns absolute zip output path from arguments"""
        return self._get_path(self.options.zip_output_path,
                              relative_root_path=self.project_path,
                              fallback_path=[self.program_path, 'dist'])

    # remote arguments
    def get_remote_temp_path(self) -> str:
        return self._get_path(self.options.remote_temp_path,
                              relative_root_path=self.project_path,
                              fallback_path=[self.program_path, 'remote'])

    # program arguments
    def get_game_type(self) -> str:
        """Returns game type from arguments or Papyrus Project"""
        if self.options.game_type:
            game_type = self.options.game_type.casefold()
            if game_type and game_type in self.game_types:
                return game_type

        if self.options.game_path:
            game_path = self.options.game_path.casefold()
            if game_path.endswith('fallout 4'):
                ProjectBase.log.warning('Using game type: Fallout 4 (determined from game path)')
                return 'fo4'
            if game_path.endswith('skyrim special edition'):
                ProjectBase.log.warning('Using game type: Skyrim Special Edition (determined from game path)')
                return 'sse'
            if game_path.endswith('skyrim'):
                ProjectBase.log.warning('Using game type: Skyrim (determined from game path)')
                return 'tesv'

        if self.options.registry_path:
            registry_path_parts = self.options.registry_path.casefold().split(os.sep)
            if 'fallout 4' in registry_path_parts:
                ProjectBase.log.warning('Using game type: Fallout 4 (determined from registry path)')
                return 'fo4'
            if 'skyrim special edition' in registry_path_parts:
                ProjectBase.log.warning('Using game type: Skyrim Special Edition (determined from registry path)')
                return 'sse'
            if 'skyrim' in registry_path_parts:
                ProjectBase.log.warning('Using game type: Skyrim (determined from registry path)')
                return 'tesv'

        if self.import_paths:
            for import_path in reversed(self.import_paths):
                path_parts: list = import_path.casefold().split(os.sep)
                if 'fallout 4' in path_parts:
                    ProjectBase.log.warning('Using game type: Fallout 4 (determined from import paths)')
                    return 'fo4'
                if 'skyrim special edition' in path_parts:
                    ProjectBase.log.warning('Using game type: Skyrim Special Edition (determined from import paths)')
                    return 'sse'
                if 'skyrim' in path_parts:
                    ProjectBase.log.warning('Using game type: Skyrim (determined from import paths)')
                    return 'tesv'

        if self.options.flags_path:
            flags_path = self.options.flags_path.casefold()
            if flags_path.endswith('institute_papyrus_flags.flg'):
                ProjectBase.log.warning('Using game type: Fallout 4 (determined from flags path)')
                return 'fo4'
            if flags_path.endswith('tesv_papyrus_flags.flg'):
                try:
                    self.get_game_path('sse')
                except FileNotFoundError:
                    ProjectBase.log.warning('Using game type: Skyrim (determined from flags path)')
                    return 'tesv'
                else:
                    ProjectBase.log.warning('Using game type: Skyrim Special Edition (determined from flags path)')
                    return 'sse'

        return ''

    def get_log_path(self) -> str:
        """Returns absolute log path from arguments"""
        return self._get_path(self.options.log_path,
                              relative_root_path=os.getcwd(),
                              fallback_path=[self.program_path, 'logs'])
