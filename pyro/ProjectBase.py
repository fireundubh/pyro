import logging
import os
import sys
from typing import Union

from pyro.Comparators import (endswith,
                              startswith)
from pyro.Constants import (FlagsName,
                            GameName,
                            GameType)
from pyro.ProjectOptions import ProjectOptions
from pyro.StringTemplate import StringTemplate


class ProjectBase:
    log: logging.Logger = logging.getLogger('pyro')

    options: ProjectOptions

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
        if endswith(sys.argv[0], ('pyro', '.exe')):
            self.program_path = os.path.abspath(os.path.join(self.program_path, os.pardir))

        self.project_name = os.path.splitext(os.path.basename(self.options.input_path))[0]
        self.project_path = os.path.dirname(self.options.input_path)
        os.chdir(self.project_path)

    def __setattr__(self, key: str, value: object) -> None:
        if isinstance(value, str) and endswith(key, 'path'):
            if os.altsep in value:
                value = os.path.normpath(value)
        elif isinstance(value, list) and endswith(key, 'paths'):
            value = [os.path.normpath(path) if path != os.curdir else path for path in value]
        super(ProjectBase, self).__setattr__(key, value)

    @staticmethod
    def _get_path(path: str, *, relative_root_path: str, fallback_path: Union[str, list]) -> str:
        """
        Returns absolute path from path or fallback path if path empty or unset

        :param path: A relative or absolute path
        :param relative_root_path: Absolute path to directory to join with relative path
        :param fallback_path: Absolute path to return if path empty or unset
        """
        if path or startswith(path, (os.curdir, os.pardir)):
            path = os.path.expanduser(os.path.expandvars(path))
            return os.path.normpath(path) if os.path.isabs(path) else os.path.normpath(os.path.join(relative_root_path, path))
        if isinstance(fallback_path, list):
            return os.path.abspath(os.path.join(*fallback_path))
        return fallback_path

    def parse(self, value: str) -> str:
        """Expands string tokens and environment variables, and returns the parsed string"""
        t = StringTemplate(value)
        try:
            retval = os.path.expanduser(os.path.expandvars(t.substitute(self.variables)))
            if os.path.isabs(retval):
                retval = os.path.normpath(retval)
            return retval
        except KeyError as e:
            ProjectBase.log.error(f'Failed to parse variable "{e.args[0]}" in "{value}". Is the variable name correct?')
            sys.exit(1)

    # build arguments
    def get_worker_limit(self) -> int:
        """
        Returns worker limit from arguments

        Used by: BuildFacade
        """
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
        """
        Returns absolute compiler path from arguments

        Used by: BuildFacade
        """
        return self._get_path(self.options.compiler_path,
                              relative_root_path=os.getcwd(),
                              fallback_path=[self.options.game_path, 'Papyrus Compiler', 'PapyrusCompiler.exe'])

    def get_compiler_config_path(self) -> str:
        """Returns absolute compiler config file path from arguments"""
        return self._get_path(self.options.compiler_config_path,
                              relative_root_path=os.getcwd(),
                              fallback_path=[self.program_path, 'tools', 'caprica.cfg'])

    def get_flags_path(self) -> str:
        """
        Returns absolute flags path or flags file name from arguments or game path

        Used by: BuildFacade
        """
        if self.options.flags_path:
            if startswith(self.options.flags_path, tuple(FlagsName.values()), ignorecase=True):
                return self.options.flags_path
            if os.path.isabs(self.options.flags_path):
                return self.options.flags_path
            return os.path.join(self.project_path, self.options.flags_path)

        if self.options.game_path:
            if endswith(self.options.game_path, GameName.FO4, ignorecase=True):
                return FlagsName.FO4
            if endswith(self.options.game_path, GameName.SF1, ignorecase=True):
                return FlagsName.SF1

        return FlagsName.TES5

    def get_output_path(self) -> str:
        """
        Returns absolute output path from arguments

        Used by: BuildFacade
        """
        return self._get_path(self.options.output_path,
                              relative_root_path=self.project_path,
                              fallback_path=[self.program_path, 'out'])

    # game arguments
    def get_game_path(self, game_type: str = '') -> str:
        """
        Returns absolute game path from arguments or Windows Registry

        Used by: BuildFacade, ProjectBase
        """
        if self.options.game_path:
            if os.path.isabs(self.options.game_path):
                return self.options.game_path
            return os.path.join(os.getcwd(), self.options.game_path)

        if sys.platform == 'win32':
            return self.get_installed_path(game_type)

        raise FileNotFoundError('Cannot determine game path')

    def get_registry_path(self, game_type: str = '') -> str:
        """Returns path to game installed path in Windows Registry from game type"""
        if not self.options.registry_path:
            game_type = self.options.game_type if not game_type else game_type
            if game_type in GameType.values():
                game_name = GameName.get(game_type)
            else:
                raise KeyError('Cannot determine registry path from game type')
            if startswith(game_name, 'Starfield'):
                return r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 1716740\InstallLocation'
            if startswith(game_name, 'Fallout'):
                game_name = game_name.replace(' ', '')
            return rf'HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Bethesda Softworks\{game_name}\Installed Path'
        return self.options.registry_path.replace('/', '\\')

    def get_installed_path(self, game_type: str = '') -> str:
        """
        Returns path to game installed path in Windows Registry

        Used by: BuildFacade, ProjectBase
        """
        import winreg

        registry_path, registry_type = self.options.registry_path, winreg.HKEY_LOCAL_MACHINE

        game_type = self.options.game_type if not game_type else game_type

        if not registry_path:
            registry_path = self.get_registry_path(game_type)

        hkey, key_path = registry_path.split(os.sep, maxsplit=1)
        key_head, key_tail = os.path.split(key_path)

        # fix absolute registry paths, if needed
        if any(hkey == value for value in ('HKCU', 'HKEY_CURRENT_USER')):
            registry_type = winreg.HKEY_CURRENT_USER

        try:
            registry_key = winreg.OpenKey(registry_type, key_head, 0, winreg.KEY_READ)
            reg_value, _ = winreg.QueryValueEx(registry_key, key_tail)
            winreg.CloseKey(registry_key)
        except WindowsError:
            ProjectBase.log.error(f'Installed Path for {game_type} '
                                  f'does not exist in Windows Registry. Run the game launcher once, then try again.')
            sys.exit(1)

        # noinspection PyUnboundLocalVariable
        if not os.path.isdir(reg_value):
            ProjectBase.log.error(f'Installed Path for {game_type} does not exist: {reg_value}')
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

    @staticmethod
    def _get_game_type_from_path(path: str) -> str:
        parts: list = path.casefold().split(os.sep)
        if GameName.SF1.casefold() in parts:
            return GameType.SF1
        if GameName.SF1.casefold().replace(' ', '') in parts:
            return GameType.SF1
        if GameName.FO4.casefold() in parts:
            return GameType.FO4
        if GameName.FO4.casefold().replace(' ', '') in parts:
            return GameType.FO4
        if GameName.SSE.casefold() in parts:
            return GameType.SSE
        if GameName.TES5.casefold() in parts:
            return GameType.TES5
        return ''

    # program arguments
    def get_game_type(self) -> str:
        """Returns game type from arguments or Papyrus Project"""
        if self.options.game_type:
            return self.options.game_type

        if self.options.game_path:
            for game_type, game_name in GameName.items():
                if endswith(self.options.game_path, game_name, ignorecase=True):
                    ProjectBase.log.info(f'Using game type: {game_name} (determined from game path)')
                    return GameType.get(game_type)

        if self.options.registry_path:
            game_type = self._get_game_type_from_path(self.options.registry_path)
            if game_type:
                ProjectBase.log.info(f'Using game type: {GameName.get(game_type)} (determined from registry path)')
                return game_type

        if self.import_paths:
            for import_path in reversed(self.import_paths):
                game_type = self._get_game_type_from_path(import_path)
                if game_type:
                    ProjectBase.log.info(f'Using game type: {GameName.get(game_type)} (determined from import paths)')
                    return game_type

        if self.options.flags_path:
            if endswith(self.options.flags_path, FlagsName.SF1, ignorecase=True):
                ProjectBase.log.info(f'Using game type: {GameName.FO4} (determined from flags path)')
                return GameType.SF1

            if endswith(self.options.flags_path, FlagsName.FO4, ignorecase=True):
                ProjectBase.log.info(f'Using game type: {GameName.FO4} (determined from flags path)')
                return GameType.FO4

            if endswith(self.options.flags_path, FlagsName.TES5, ignorecase=True):
                try:
                    self.get_game_path('sse')
                except FileNotFoundError:
                    ProjectBase.log.info(f'Using game type: {GameName.TES5} (determined from flags path)')
                    return GameType.TES5
                else:
                    ProjectBase.log.info(f'Using game type: {GameName.SSE} (determined from flags path)')
                    return GameType.SSE

        raise AssertionError('Cannot determine game type from game path, registry path, import paths, or flags path')

    def get_log_path(self) -> str:
        """Returns absolute log path from arguments"""
        return self._get_path(self.options.log_path,
                              relative_root_path=os.getcwd(),
                              fallback_path=[self.program_path, 'logs'])
