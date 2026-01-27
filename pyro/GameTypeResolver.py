"""
GameTypeResolver - Handles game type detection from multiple sources.

Extracted from PapyrusProject.try_set_game_type() and ProjectBase.get_game_type().
Implements a 5-tier detection hierarchy:
1. CLI argument (--game-type)
2. XML Game attribute
3. Game path
4. Registry path
5. Import paths
6. Flags path
"""
import logging
import os
import sys
from typing import TYPE_CHECKING

from pyro.Comparators import endswith
from pyro.Constants import FlagsName, GameName, GameType
from pyro.Exceptions import GameTypeError

if TYPE_CHECKING:
    from pyro.ProjectOptions import ProjectOptions


class GameTypeResolver:
    """
    Resolves the game type (fo4, sf1, sse, tes5) from multiple sources.

    Detection priority:
    1. CLI argument (--game-type)
    2. XML Game attribute in PPJ
    3. Game path inspection
    4. Registry path inspection
    5. Import paths inspection
    6. Flags path inspection
    """

    log: logging.Logger = logging.getLogger('pyro')

    def __init__(self, options: 'ProjectOptions', import_paths: list[str] | None = None) -> None:
        """
        Initialize the game type resolver.

        Args:
            options: Project options containing game_type, game_path, registry_path, flags_path
            import_paths: List of import paths for type detection
        """
        self.options = options
        self.import_paths = import_paths or []

    @staticmethod
    def _get_game_type_from_path(path: str) -> str:
        """
        Detect game type from a path by looking for game-specific folder names.

        Args:
            path: File system path to inspect

        Returns:
            Game type string (fo4, sf1, sse, tes5) or empty string if not detected
        """
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

    def detect_from_game_path(self) -> str | None:
        """
        Detect game type from the game path option.

        Returns:
            Game type string or None if not detected
        """
        if not self.options.game_path:
            return None

        for game_type, game_name in GameName.items():
            if endswith(self.options.game_path, game_name, ignorecase=True):
                self.log.info(f'Using game type: {game_name} (determined from game path)')
                return GameType.get(game_type)

        return None

    def detect_from_registry_path(self) -> str | None:
        """
        Detect game type from the registry path option.

        Returns:
            Game type string or None if not detected
        """
        if not self.options.registry_path:
            return None

        game_type = self._get_game_type_from_path(self.options.registry_path)
        if game_type:
            self.log.info(f'Using game type: {GameName.get(game_type)} (determined from registry path)')
            return game_type

        return None

    def detect_from_import_paths(self) -> str | None:
        """
        Detect game type from import paths.

        Returns:
            Game type string or None if not detected
        """
        if not self.import_paths:
            return None

        for import_path in reversed(self.import_paths):
            game_type = self._get_game_type_from_path(import_path)
            if game_type:
                self.log.info(f'Using game type: {GameName.get(game_type)} (determined from import paths)')
                return game_type

        return None

    def detect_from_flags_path(self, get_game_path_fn=None) -> str | None:
        """
        Detect game type from the flags path option.

        Args:
            get_game_path_fn: Optional function to check if SSE is installed (for TES5/SSE disambiguation)

        Returns:
            Game type string or None if not detected
        """
        if not self.options.flags_path:
            return None

        if endswith(self.options.flags_path, FlagsName.SF1, ignorecase=True):
            self.log.info(f'Using game type: {GameName.SF1} (determined from flags path)')
            return GameType.SF1

        if endswith(self.options.flags_path, FlagsName.FO4, ignorecase=True):
            self.log.info(f'Using game type: {GameName.FO4} (determined from flags path)')
            return GameType.FO4

        if endswith(self.options.flags_path, FlagsName.TES5, ignorecase=True):
            # TES5 and SSE share the same flags file
            # Try to determine which by checking if SSE is installed
            if get_game_path_fn:
                try:
                    get_game_path_fn('sse')
                    self.log.info(f'Using game type: {GameName.SSE} (determined from flags path)')
                    return GameType.SSE
                except (FileNotFoundError, Exception):
                    pass

            self.log.info(f'Using game type: {GameName.TES5} (determined from flags path)')
            return GameType.TES5

        return None

    def detect_from_xml_attribute(self, xml_game_type: str) -> str | None:
        """
        Detect game type from the XML Game attribute.

        Args:
            xml_game_type: The Game attribute value from the PPJ file

        Returns:
            Game type string or None if not valid
        """
        if not xml_game_type:
            return None

        game_type = GameType.get(xml_game_type)
        if game_type:
            self.log.info(f'Using game type: {GameName.get(xml_game_type)} (determined from Papyrus Project)')
            return game_type

        return None

    def resolve(self, xml_game_type: str = '', get_game_path_fn=None) -> str:
        """
        Resolve the game type using the detection hierarchy.

        Args:
            xml_game_type: The Game attribute value from the PPJ file
            get_game_path_fn: Optional function to check game installation (for TES5/SSE disambiguation)

        Returns:
            The resolved game type string

        Raises:
            GameTypeError: If game type cannot be determined from any source
        """
        # Priority 1: CLI argument (already set in options.game_type)
        if self.options.game_type in GameType.values():
            return self.options.game_type

        # Priority 2: XML Game attribute
        result = self.detect_from_xml_attribute(xml_game_type)
        if result:
            return result

        # Priority 3: Game path
        result = self.detect_from_game_path()
        if result:
            return result

        # Priority 4: Registry path
        result = self.detect_from_registry_path()
        if result:
            return result

        # Priority 5: Import paths
        result = self.detect_from_import_paths()
        if result:
            return result

        # Priority 6: Flags path
        result = self.detect_from_flags_path(get_game_path_fn)
        if result:
            return result

        raise GameTypeError('Cannot determine game type from arguments or Papyrus Project')
