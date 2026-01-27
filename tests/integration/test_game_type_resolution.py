"""
Integration tests for GameTypeResolver.
Tests the 5-tier game type detection hierarchy.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from lxml import etree

from pyro.Constants import GameType, GameName, FlagsName
from pyro.Exceptions import GameTypeError
from pyro.GameTypeResolver import GameTypeResolver


class TestDetectFromPath:
    """Test game type detection from file paths."""

    def test_detect_starfield_from_path(self):
        """Test detecting Starfield from path."""
        result = GameTypeResolver._get_game_type_from_path('C:\\Games\\Starfield\\Data')

        assert result == GameType.SF1

    def test_detect_starfield_no_space(self):
        """Test detecting Starfield without space."""
        result = GameTypeResolver._get_game_type_from_path('C:\\Games\\starfield\\data')

        assert result == GameType.SF1

    def test_detect_fallout4_from_path(self):
        """Test detecting Fallout 4 from path."""
        result = GameTypeResolver._get_game_type_from_path('C:\\Games\\Fallout 4\\Data')

        assert result == GameType.FO4

    def test_detect_skyrim_se_from_path(self):
        """Test detecting Skyrim SE from path."""
        result = GameTypeResolver._get_game_type_from_path('C:\\Games\\Skyrim Special Edition\\Data')

        assert result == GameType.SSE

    def test_detect_skyrim_le_from_path(self):
        """Test detecting Skyrim LE from path."""
        result = GameTypeResolver._get_game_type_from_path('C:\\Games\\Skyrim\\Data')

        assert result == GameType.TES5

    def test_no_detection_from_unrelated_path(self):
        """Test that unrelated paths return empty string."""
        result = GameTypeResolver._get_game_type_from_path('C:\\Projects\\MyMod\\Scripts')

        assert result == ''


class TestDetectFromGamePath:
    """Test detection from game_path option."""

    def test_detect_sse_from_game_path(self):
        """Test detecting SSE from game path."""
        options = MagicMock()
        options.game_path = 'C:\\Steam\\steamapps\\common\\Skyrim Special Edition'
        options.registry_path = ''
        options.flags_path = ''
        options.game_type = ''

        resolver = GameTypeResolver(options)
        result = resolver.detect_from_game_path()

        assert result == GameType.SSE

    def test_detect_fo4_from_game_path(self):
        """Test detecting FO4 from game path."""
        options = MagicMock()
        options.game_path = 'C:\\Steam\\steamapps\\common\\Fallout 4'
        options.registry_path = ''
        options.flags_path = ''
        options.game_type = ''

        resolver = GameTypeResolver(options)
        result = resolver.detect_from_game_path()

        assert result == GameType.FO4

    def test_no_detection_without_game_path(self):
        """Test that missing game_path returns None."""
        options = MagicMock()
        options.game_path = ''
        options.registry_path = ''
        options.flags_path = ''
        options.game_type = ''

        resolver = GameTypeResolver(options)
        result = resolver.detect_from_game_path()

        assert result is None


class TestDetectFromRegistryPath:
    """Test detection from registry_path option."""

    def test_detect_from_registry_path(self):
        """Test detecting game type from registry path."""
        options = MagicMock()
        options.game_path = ''
        options.registry_path = 'HKEY_LOCAL_MACHINE\\SOFTWARE\\Bethesda Softworks\\Skyrim Special Edition'
        options.flags_path = ''
        options.game_type = ''

        resolver = GameTypeResolver(options)
        result = resolver.detect_from_registry_path()

        assert result == GameType.SSE

    def test_no_detection_without_registry_path(self):
        """Test that missing registry_path returns None."""
        options = MagicMock()
        options.game_path = ''
        options.registry_path = ''
        options.flags_path = ''
        options.game_type = ''

        resolver = GameTypeResolver(options)
        result = resolver.detect_from_registry_path()

        assert result is None


class TestDetectFromImportPaths:
    """Test detection from import paths."""

    def test_detect_from_import_paths(self):
        """Test detecting game type from import paths."""
        options = MagicMock()
        options.game_path = ''
        options.registry_path = ''
        options.flags_path = ''
        options.game_type = ''

        import_paths = [
            'C:\\MyProject\\Source',
            'C:\\Steam\\steamapps\\common\\Skyrim Special Edition\\Data\\Scripts\\Source',
        ]

        resolver = GameTypeResolver(options, import_paths)
        result = resolver.detect_from_import_paths()

        assert result == GameType.SSE

    def test_uses_last_matching_import(self):
        """Test that the last matching import path is used."""
        options = MagicMock()
        options.game_path = ''
        options.registry_path = ''
        options.flags_path = ''
        options.game_type = ''

        import_paths = [
            'C:\\Steam\\steamapps\\common\\Skyrim\\Data\\Scripts\\Source',  # TES5
            'C:\\Steam\\steamapps\\common\\Skyrim Special Edition\\Data\\Scripts\\Source',  # SSE
        ]

        resolver = GameTypeResolver(options, import_paths)
        result = resolver.detect_from_import_paths()

        # Should return SSE (last in list, first checked due to reversed())
        assert result == GameType.SSE

    def test_no_detection_without_import_paths(self):
        """Test that empty import_paths returns None."""
        options = MagicMock()
        options.game_path = ''
        options.registry_path = ''
        options.flags_path = ''
        options.game_type = ''

        resolver = GameTypeResolver(options, [])
        result = resolver.detect_from_import_paths()

        assert result is None


class TestDetectFromFlagsPath:
    """Test detection from flags_path option."""

    def test_detect_sf1_from_flags(self):
        """Test detecting SF1 from Starfield flags."""
        options = MagicMock()
        options.game_path = ''
        options.registry_path = ''
        options.flags_path = 'Starfield_Papyrus_Flags.flg'
        options.game_type = ''

        resolver = GameTypeResolver(options)
        result = resolver.detect_from_flags_path()

        assert result == GameType.SF1

    def test_detect_fo4_from_flags(self):
        """Test detecting FO4 from Institute flags."""
        options = MagicMock()
        options.game_path = ''
        options.registry_path = ''
        options.flags_path = 'Institute_Papyrus_Flags.flg'
        options.game_type = ''

        resolver = GameTypeResolver(options)
        result = resolver.detect_from_flags_path()

        assert result == GameType.FO4

    def test_detect_tes5_from_flags_without_sse(self):
        """Test detecting TES5 when SSE is not installed."""
        options = MagicMock()
        options.game_path = ''
        options.registry_path = ''
        options.flags_path = 'TESV_Papyrus_Flags.flg'
        options.game_type = ''

        def get_game_path_raises(game_type):
            raise FileNotFoundError()

        resolver = GameTypeResolver(options)
        result = resolver.detect_from_flags_path(get_game_path_raises)

        assert result == GameType.TES5

    def test_detect_sse_from_flags_with_sse_installed(self):
        """Test detecting SSE when SSE is installed."""
        options = MagicMock()
        options.game_path = ''
        options.registry_path = ''
        options.flags_path = 'TESV_Papyrus_Flags.flg'
        options.game_type = ''

        def get_game_path_works(game_type):
            return 'C:\\Games\\Skyrim Special Edition'

        resolver = GameTypeResolver(options)
        result = resolver.detect_from_flags_path(get_game_path_works)

        assert result == GameType.SSE


class TestDetectFromXmlAttribute:
    """Test detection from XML Game attribute."""

    def test_detect_sse_from_xml(self):
        """Test detecting SSE from XML attribute."""
        options = MagicMock()
        options.game_path = ''
        options.registry_path = ''
        options.flags_path = ''
        options.game_type = ''

        resolver = GameTypeResolver(options)
        result = resolver.detect_from_xml_attribute('SSE')

        assert result == GameType.SSE

    def test_detect_fo4_from_xml(self):
        """Test detecting FO4 from XML attribute."""
        options = MagicMock()
        options.game_path = ''
        options.registry_path = ''
        options.flags_path = ''
        options.game_type = ''

        resolver = GameTypeResolver(options)
        result = resolver.detect_from_xml_attribute('fo4')

        assert result == GameType.FO4

    def test_empty_xml_attribute_returns_none(self):
        """Test that empty XML attribute returns None."""
        options = MagicMock()
        options.game_path = ''
        options.registry_path = ''
        options.flags_path = ''
        options.game_type = ''

        resolver = GameTypeResolver(options)
        result = resolver.detect_from_xml_attribute('')

        assert result is None


class TestResolveHierarchy:
    """Test the full resolution hierarchy."""

    def test_cli_argument_takes_priority(self):
        """Test that CLI argument has highest priority."""
        options = MagicMock()
        options.game_type = GameType.FO4  # CLI argument
        options.game_path = 'C:\\Games\\Skyrim Special Edition'  # Would detect SSE
        options.registry_path = ''
        options.flags_path = ''

        resolver = GameTypeResolver(options)
        result = resolver.resolve(xml_game_type='sse')  # XML says SSE

        # Should still be FO4 from CLI
        assert result == GameType.FO4

    def test_xml_over_game_path(self):
        """Test that XML attribute has priority over game path."""
        options = MagicMock()
        options.game_type = ''  # No CLI argument
        options.game_path = 'C:\\Games\\Skyrim Special Edition'  # Would detect SSE
        options.registry_path = ''
        options.flags_path = ''

        resolver = GameTypeResolver(options)
        result = resolver.resolve(xml_game_type='fo4')  # XML says FO4

        assert result == GameType.FO4

    def test_game_path_over_import_paths(self):
        """Test that game_path has priority over import paths."""
        options = MagicMock()
        options.game_type = ''
        options.game_path = 'C:\\Games\\Fallout 4'  # Would detect FO4
        options.registry_path = ''
        options.flags_path = ''

        import_paths = ['C:\\Games\\Skyrim Special Edition\\Data\\Scripts\\Source']

        resolver = GameTypeResolver(options, import_paths)
        result = resolver.resolve()

        assert result == GameType.FO4

    def test_raises_when_no_detection(self):
        """Test that error is raised when no detection succeeds."""
        options = MagicMock()
        options.game_type = ''
        options.game_path = ''
        options.registry_path = ''
        options.flags_path = ''

        resolver = GameTypeResolver(options, [])

        with pytest.raises(GameTypeError, match='Cannot determine game type'):
            resolver.resolve()


class TestIntegrationWithRealProject:
    """Integration tests using real project files."""

    def test_utf8_project_game_type(self, utf8_project_path: Path):
        """Test game type detection from utf8 project (has Game='SSE')."""
        tree = etree.parse(str(utf8_project_path))
        root = tree.getroot()

        # Get Game attribute from root
        game_attr = root.get('Game', '')

        options = MagicMock()
        options.game_type = ''
        options.game_path = ''
        options.registry_path = ''
        options.flags_path = ''

        resolver = GameTypeResolver(options)
        result = resolver.detect_from_xml_attribute(game_attr)

        assert result == GameType.SSE

    def test_fo4_project_game_type(self, fo4_autohelmet_project_path: Path):
        """Test game type detection from FO4 project."""
        if not fo4_autohelmet_project_path.exists():
            pytest.skip("FO4 project not found")

        tree = etree.parse(str(fo4_autohelmet_project_path))
        root = tree.getroot()

        # Get Game attribute from root
        game_attr = root.get('Game', '')

        if not game_attr:
            pytest.skip("FO4 project doesn't have Game attribute")

        options = MagicMock()
        options.game_type = ''
        options.game_path = ''
        options.registry_path = ''
        options.flags_path = ''

        resolver = GameTypeResolver(options)
        result = resolver.detect_from_xml_attribute(game_attr)

        assert result == GameType.FO4
