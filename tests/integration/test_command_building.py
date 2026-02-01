"""
Integration tests for CompilerCommandBuilder.
Tests verify command generation without actual compilation.
"""
from unittest.mock import MagicMock, PropertyMock

import pytest

from pyro.Constants import GameType
from pyro.CompilerCommandBuilder import CompilerCommandBuilder


class TestCompilerDetection:
    """Test compiler type detection."""

    def test_detect_standard_compiler(self):
        """Test detecting standard Papyrus compiler."""
        ppj = MagicMock()
        ppj.get_compiler_path.return_value = 'C:\\Skyrim\\Papyrus Compiler\\PapyrusCompiler.exe'

        builder = CompilerCommandBuilder(ppj)

        assert not builder.is_using_caprica()

    def test_detect_caprica_compiler(self):
        """Test detecting Caprica compiler."""
        ppj = MagicMock()
        ppj.get_compiler_path.return_value = 'C:\\Tools\\Caprica.exe'

        builder = CompilerCommandBuilder(ppj)

        assert builder.is_using_caprica()

    def test_detect_caprica_case_insensitive(self):
        """Test that Caprica detection is case insensitive."""
        ppj = MagicMock()
        ppj.get_compiler_path.return_value = 'C:\\Tools\\CAPRICA.EXE'

        builder = CompilerCommandBuilder(ppj)

        assert builder.is_using_caprica()


class TestGameNameForCaprica:
    """Test game name generation for Caprica compiler."""

    def test_fallout4_game_name(self):
        """Test FO4 game name for Caprica."""
        ppj = MagicMock()
        ppj.options = MagicMock()
        ppj.options.game_type = GameType.FO4

        builder = CompilerCommandBuilder(ppj)
        result = builder.get_game_name_for_caprica()

        assert result == 'fallout4'

    def test_skyrim_le_game_name(self):
        """Test TES5 game name for Caprica."""
        ppj = MagicMock()
        ppj.options = MagicMock()
        ppj.options.game_type = GameType.TES5

        builder = CompilerCommandBuilder(ppj)
        result = builder.get_game_name_for_caprica()

        assert result == 'skyrim'

    def test_skyrim_se_game_name(self):
        """Test SSE game name for Caprica."""
        ppj = MagicMock()
        ppj.options = MagicMock()
        ppj.options.game_type = GameType.SSE

        builder = CompilerCommandBuilder(ppj)
        result = builder.get_game_name_for_caprica()

        assert result == 'skyrim'

    def test_starfield_game_name(self):
        """Test SF1 game name for Caprica."""
        ppj = MagicMock()
        ppj.options = MagicMock()
        ppj.options.game_type = GameType.SF1

        builder = CompilerCommandBuilder(ppj)
        result = builder.get_game_name_for_caprica()

        assert result == 'starfield'


class TestStandardCommandBuilding:
    """Test standard compiler command building."""

    def test_build_single_script_command(self):
        """Test building command for a single script."""
        ppj = MagicMock()
        ppj.get_compiler_path.return_value = 'C:\\Compiler\\PapyrusCompiler.exe'
        ppj.get_flags_path.return_value = 'TESV_Papyrus_Flags.flg'
        ppj.get_output_path.return_value = 'C:\\Output'
        ppj.import_paths = ['C:\\Source', 'C:\\SkyrimSource']
        ppj.options = MagicMock()
        ppj.options.game_type = GameType.SSE
        ppj.release = False
        ppj.final = False
        ppj.optimize = False

        builder = CompilerCommandBuilder(ppj)
        psc_paths = {'TestScript': 'C:\\Source\\TestScript.psc'}

        count, commands = builder.build_standard_commands(psc_paths)

        assert count == 1
        assert len(commands) == 1
        assert isinstance(commands[0], list)
        assert '"C:\\Compiler\\PapyrusCompiler.exe"' in commands[0]
        assert '"C:\\Source\\TestScript.psc"' in commands[0]
        assert any('-f=' in arg for arg in commands[0])
        assert any('-i=' in arg for arg in commands[0])
        assert any('-o=' in arg for arg in commands[0])

    def test_build_multiple_script_commands(self):
        """Test building commands for multiple scripts."""
        ppj = MagicMock()
        ppj.get_compiler_path.return_value = 'C:\\Compiler\\PapyrusCompiler.exe'
        ppj.get_flags_path.return_value = 'TESV_Papyrus_Flags.flg'
        ppj.get_output_path.return_value = 'C:\\Output'
        ppj.import_paths = ['C:\\Source']
        ppj.options = MagicMock()
        ppj.options.game_type = GameType.SSE
        ppj.release = False
        ppj.final = False
        ppj.optimize = False

        builder = CompilerCommandBuilder(ppj)
        psc_paths = {
            'Script1': 'C:\\Source\\Script1.psc',
            'Script2': 'C:\\Source\\Script2.psc',
            'Script3': 'C:\\Source\\Script3.psc',
        }

        count, commands = builder.build_standard_commands(psc_paths)

        assert count == 3
        assert len(commands) == 3

    def test_fo4_uses_object_name(self):
        """Test that FO4 uses object name instead of path."""
        ppj = MagicMock()
        ppj.get_compiler_path.return_value = 'C:\\Compiler\\PapyrusCompiler.exe'
        ppj.get_flags_path.return_value = 'Institute_Papyrus_Flags.flg'
        ppj.get_output_path.return_value = 'C:\\Output'
        ppj.import_paths = ['C:\\Source']
        ppj.options = MagicMock()
        ppj.options.game_type = GameType.FO4
        ppj.release = False
        ppj.final = False
        ppj.optimize = False

        builder = CompilerCommandBuilder(ppj)
        psc_paths = {'Namespace:Script': 'C:\\Source\\Namespace\\Script.psc'}

        count, commands = builder.build_standard_commands(psc_paths)

        assert count == 1
        assert '"Namespace:Script"' in commands[0]
        assert not any('Script.psc' in arg for arg in commands[0])  # Uses object name, not path

    def test_fo4_release_flag(self):
        """Test that FO4 release flag is added."""
        ppj = MagicMock()
        ppj.get_compiler_path.return_value = 'C:\\Compiler\\PapyrusCompiler.exe'
        ppj.get_flags_path.return_value = 'Institute_Papyrus_Flags.flg'
        ppj.get_output_path.return_value = 'C:\\Output'
        ppj.import_paths = ['C:\\Source']
        ppj.options = MagicMock()
        ppj.options.game_type = GameType.FO4
        ppj.release = True
        ppj.final = False
        ppj.optimize = False

        builder = CompilerCommandBuilder(ppj)
        psc_paths = {'Script': 'C:\\Source\\Script.psc'}

        count, commands = builder.build_standard_commands(psc_paths)

        assert isinstance(commands[0], list)
        assert '-release' in commands[0]

    def test_fo4_final_flag(self):
        """Test that FO4 final flag is added."""
        ppj = MagicMock()
        ppj.get_compiler_path.return_value = 'C:\\Compiler\\PapyrusCompiler.exe'
        ppj.get_flags_path.return_value = 'Institute_Papyrus_Flags.flg'
        ppj.get_output_path.return_value = 'C:\\Output'
        ppj.import_paths = ['C:\\Source']
        ppj.options = MagicMock()
        ppj.options.game_type = GameType.FO4
        ppj.release = False
        ppj.final = True
        ppj.optimize = False

        builder = CompilerCommandBuilder(ppj)
        psc_paths = {'Script': 'C:\\Source\\Script.psc'}

        count, commands = builder.build_standard_commands(psc_paths)

        assert isinstance(commands[0], list)
        assert '-final' in commands[0]

    def test_optimize_flag(self):
        """Test that optimize flag is added."""
        ppj = MagicMock()
        ppj.get_compiler_path.return_value = 'C:\\Compiler\\PapyrusCompiler.exe'
        ppj.get_flags_path.return_value = 'TESV_Papyrus_Flags.flg'
        ppj.get_output_path.return_value = 'C:\\Output'
        ppj.import_paths = ['C:\\Source']
        ppj.options = MagicMock()
        ppj.options.game_type = GameType.SSE
        ppj.release = False
        ppj.final = False
        ppj.optimize = True

        builder = CompilerCommandBuilder(ppj)
        psc_paths = {'Script': 'C:\\Source\\Script.psc'}

        count, commands = builder.build_standard_commands(psc_paths)

        assert isinstance(commands[0], list)
        assert '-op' in commands[0]


class TestGetScriptsToCompile:
    """Test script selection for compilation."""

    def test_no_incremental_build(self):
        """Test that all scripts are returned when incremental build is disabled."""
        ppj = MagicMock()
        ppj.psc_paths = {'Script1': 'path1', 'Script2': 'path2'}
        ppj.missing_scripts = {}
        ppj.options = MagicMock()
        ppj.options.no_incremental_build = True

        builder = CompilerCommandBuilder(ppj)
        result = builder.get_scripts_to_compile()

        assert len(result) == 2
        assert 'Script1' in result
        assert 'Script2' in result

    def test_incremental_build_delegates_to_handler(self):
        """Test that incremental build uses script handler."""
        ppj = MagicMock()
        ppj.psc_paths = {'Script1': 'path1', 'Script2': 'path2'}
        ppj.missing_scripts = {}
        ppj.options = MagicMock()
        ppj.options.no_incremental_build = False
        ppj.script_handler = MagicMock()
        ppj.script_handler.try_exclude_unmodified_scripts.return_value = {'Script1': 'path1'}

        builder = CompilerCommandBuilder(ppj)
        result = builder.get_scripts_to_compile()

        assert len(result) == 1
        assert 'Script1' in result
        ppj.script_handler.try_exclude_unmodified_scripts.assert_called_once()

    def test_missing_scripts_added(self):
        """Test that missing scripts are added to compilation list."""
        ppj = MagicMock()
        ppj.psc_paths = {'Script1': 'path1'}
        ppj.missing_scripts = {'Script2': 'path2'}
        ppj.options = MagicMock()
        ppj.options.no_incremental_build = True

        builder = CompilerCommandBuilder(ppj)
        result = builder.get_scripts_to_compile()

        assert len(result) == 2
        assert 'Script1' in result
        assert 'Script2' in result


class TestEmptyScripts:
    """Test handling of empty script lists."""

    def test_empty_scripts_returns_zero(self):
        """Test that empty script list returns 0, []."""
        ppj = MagicMock()
        ppj.psc_paths = {}
        ppj.missing_scripts = {}
        ppj.options = MagicMock()
        ppj.options.no_incremental_build = True
        ppj.get_compiler_path.return_value = 'C:\\Compiler\\PapyrusCompiler.exe'

        builder = CompilerCommandBuilder(ppj)
        count, commands = builder.build_commands()

        assert count == 0
        assert commands == []


class TestCommandStructure:
    """Test command structure and formatting."""

    def test_paths_with_spaces_handled(self):
        """Test that paths containing spaces are properly quoted."""
        ppj = MagicMock()
        ppj.get_compiler_path.return_value = 'C:\\Program Files\\Compiler\\PapyrusCompiler.exe'
        ppj.get_flags_path.return_value = 'TESV_Papyrus_Flags.flg'
        ppj.get_output_path.return_value = 'C:\\My Output'
        ppj.import_paths = ['C:\\My Source']
        ppj.options = MagicMock()
        ppj.options.game_type = GameType.SSE
        ppj.release = False
        ppj.final = False
        ppj.optimize = False

        builder = CompilerCommandBuilder(ppj)
        psc_paths = {'Script': 'C:\\My Source\\Script.psc'}

        count, commands = builder.build_standard_commands(psc_paths)

        # Verify command is a list with properly quoted paths
        assert isinstance(commands[0], list)
        assert '"C:\\Program Files\\Compiler\\PapyrusCompiler.exe"' in commands[0]
        assert any('"C:\\My Output"' in arg for arg in commands[0])
        assert any('"C:\\My Source\\Script.psc"' in arg for arg in commands[0])

    def test_import_paths_semicolon_separated(self):
        """Test that multiple import paths are semicolon-separated."""
        ppj = MagicMock()
        ppj.get_compiler_path.return_value = 'C:\\Compiler\\PapyrusCompiler.exe'
        ppj.get_flags_path.return_value = 'TESV_Papyrus_Flags.flg'
        ppj.get_output_path.return_value = 'C:\\Output'
        ppj.import_paths = ['C:\\Source1', 'C:\\Source2', 'C:\\Source3']
        ppj.options = MagicMock()
        ppj.options.game_type = GameType.SSE
        ppj.release = False
        ppj.final = False
        ppj.optimize = False

        builder = CompilerCommandBuilder(ppj)
        psc_paths = {'Script': 'C:\\Source\\Script.psc'}

        count, commands = builder.build_standard_commands(psc_paths)

        assert isinstance(commands[0], list)
        assert any('C:\\Source1;C:\\Source2;C:\\Source3' in arg for arg in commands[0])
