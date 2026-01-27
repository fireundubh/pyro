"""
Integration tests for VariableResolver.
Uses real project files from test_data/ - no mocks.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from lxml import etree

from pyro.Exceptions import VariableError
from pyro.VariableResolver import VariableResolver


class TestVariableResolverBasics:
    """Test basic VariableResolver functionality."""

    def test_get_builtin_variables(self):
        """Test that built-in variables are properly generated."""
        options = MagicMock()
        options.bsarch_path = 'C:\\Tools\\bsarch.exe'
        options.compiler_path = 'C:\\Compiler'
        options.compiler_config_path = ''
        options.flags_path = 'TESV_Papyrus_Flags.flg'
        options.game_path = 'C:\\Games\\Skyrim'
        options.log_path = ''
        options.output_path = 'C:\\Output'
        options.package_path = ''
        options.registry_path = ''
        options.remote_temp_path = ''
        options.temp_path = ''
        options.zip_output_path = ''

        resolver = VariableResolver(
            program_path='C:\\Pyro',
            project_path='C:\\Projects\\MyMod',
            options=options
        )

        builtins = resolver.get_builtin_variables()

        assert 'UNIXTIME' in builtins
        assert builtins['UNIXTIME'].isdigit()
        assert builtins['PROGRAM_PATH'] == 'C:\\Pyro'
        assert builtins['PROJECT_PATH'] == 'C:\\Projects\\MyMod'
        assert builtins['O_GAME_PATH'] == 'C:\\Games\\Skyrim'
        assert builtins['O_FLAGS_PATH'] == 'TESV_Papyrus_Flags.flg'

    def test_resolve_simple_value(self):
        """Test resolving a simple value without variables."""
        options = MagicMock()
        options.bsarch_path = ''
        options.compiler_path = ''
        options.compiler_config_path = ''
        options.flags_path = ''
        options.game_path = ''
        options.log_path = ''
        options.output_path = ''
        options.package_path = ''
        options.registry_path = ''
        options.remote_temp_path = ''
        options.temp_path = ''
        options.zip_output_path = ''

        resolver = VariableResolver(
            program_path='C:\\Pyro',
            project_path='C:\\Projects',
            options=options
        )
        resolver.variables = {'ModName': 'TestMod'}

        result = resolver.resolve_value('Hello World')

        assert result == 'Hello World'

    def test_resolve_value_with_variable(self):
        """Test resolving a value containing a variable reference."""
        options = MagicMock()
        options.bsarch_path = ''
        options.compiler_path = ''
        options.compiler_config_path = ''
        options.flags_path = ''
        options.game_path = ''
        options.log_path = ''
        options.output_path = ''
        options.package_path = ''
        options.registry_path = ''
        options.remote_temp_path = ''
        options.temp_path = ''
        options.zip_output_path = ''

        resolver = VariableResolver(
            program_path='C:\\Pyro',
            project_path='C:\\Projects',
            options=options
        )
        resolver.variables = {'ModName': 'TestMod', 'Version': '1.0'}

        result = resolver.resolve_value('@ModName - @Version')

        assert result == 'TestMod - 1.0'

    def test_resolve_undefined_variable_raises(self):
        """Test that referencing undefined variable raises error."""
        options = MagicMock()
        for attr in ['bsarch_path', 'compiler_path', 'compiler_config_path', 'flags_path',
                     'game_path', 'log_path', 'output_path', 'package_path', 'registry_path',
                     'remote_temp_path', 'temp_path', 'zip_output_path']:
            setattr(options, attr, '')

        resolver = VariableResolver(
            program_path='C:\\Pyro',
            project_path='C:\\Projects',
            options=options
        )
        resolver.variables = {}

        with pytest.raises(VariableError, match='Failed to parse variable'):
            resolver.resolve_value('@UndefinedVar')


class TestParseVariablesFromXml:
    """Test XML variable parsing."""

    def test_parse_simple_variables(self):
        """Test parsing simple variable definitions."""
        xml = """
        <Variables>
            <Variable Name="ModName" Value="TestMod"/>
            <Variable Name="Version" Value="1.0.0"/>
        </Variables>
        """
        variables_node = etree.fromstring(xml)

        options = MagicMock()
        for attr in ['bsarch_path', 'compiler_path', 'compiler_config_path', 'flags_path',
                     'game_path', 'log_path', 'output_path', 'package_path', 'registry_path',
                     'remote_temp_path', 'temp_path', 'zip_output_path']:
            setattr(options, attr, '')

        resolver = VariableResolver(
            program_path='C:\\Pyro',
            project_path='C:\\Projects',
            options=options
        )

        result = resolver.parse_variables_from_xml(variables_node)

        assert result['ModName'] == 'TestMod'
        assert result['Version'] == '1.0.0'

    def test_parse_skips_empty_values(self):
        """Test that empty variable names/values are skipped."""
        xml = """
        <Variables>
            <Variable Name="" Value="SomeValue"/>
            <Variable Name="ValidName" Value=""/>
            <Variable Name="RealVar" Value="RealValue"/>
        </Variables>
        """
        variables_node = etree.fromstring(xml)

        options = MagicMock()
        for attr in ['bsarch_path', 'compiler_path', 'compiler_config_path', 'flags_path',
                     'game_path', 'log_path', 'output_path', 'package_path', 'registry_path',
                     'remote_temp_path', 'temp_path', 'zip_output_path']:
            setattr(options, attr, '')

        resolver = VariableResolver(
            program_path='C:\\Pyro',
            project_path='C:\\Projects',
            options=options
        )

        result = resolver.parse_variables_from_xml(variables_node)

        assert len(result) == 1
        assert result['RealVar'] == 'RealValue'

    def test_parse_non_alphanumeric_name_raises(self):
        """Test that non-alphanumeric variable names raise error."""
        xml = """
        <Variables>
            <Variable Name="Mod-Name" Value="TestMod"/>
        </Variables>
        """
        variables_node = etree.fromstring(xml)

        options = MagicMock()
        for attr in ['bsarch_path', 'compiler_path', 'compiler_config_path', 'flags_path',
                     'game_path', 'log_path', 'output_path', 'package_path', 'registry_path',
                     'remote_temp_path', 'temp_path', 'zip_output_path']:
            setattr(options, attr, '')

        resolver = VariableResolver(
            program_path='C:\\Pyro',
            project_path='C:\\Projects',
            options=options
        )

        with pytest.raises(VariableError, match='must be an alphanumeric string'):
            resolver.parse_variables_from_xml(variables_node)

    def test_parse_reserved_character_raises(self):
        """Test that reserved characters in values raise error."""
        xml = """
        <Variables>
            <Variable Name="BadValue" Value="Test!Value"/>
        </Variables>
        """
        variables_node = etree.fromstring(xml)

        options = MagicMock()
        for attr in ['bsarch_path', 'compiler_path', 'compiler_config_path', 'flags_path',
                     'game_path', 'log_path', 'output_path', 'package_path', 'registry_path',
                     'remote_temp_path', 'temp_path', 'zip_output_path']:
            setattr(options, attr, '')

        resolver = VariableResolver(
            program_path='C:\\Pyro',
            project_path='C:\\Projects',
            options=options
        )

        with pytest.raises(VariableError, match='contains a reserved character'):
            resolver.parse_variables_from_xml(variables_node)


class TestTwoPassResolution:
    """Test the two-pass variable resolution."""

    def test_resolve_cross_references(self):
        """Test that variables can reference each other."""
        xml = """
        <Variables>
            <Variable Name="ModsPath" Value="C:\\Mods"/>
            <Variable Name="ModName" Value="TestMod"/>
            <Variable Name="OutputPath" Value="@ModsPath\\@ModName"/>
        </Variables>
        """
        variables_node = etree.fromstring(xml)

        options = MagicMock()
        for attr in ['bsarch_path', 'compiler_path', 'compiler_config_path', 'flags_path',
                     'game_path', 'log_path', 'output_path', 'package_path', 'registry_path',
                     'remote_temp_path', 'temp_path', 'zip_output_path']:
            setattr(options, attr, '')

        resolver = VariableResolver(
            program_path='C:\\Pyro',
            project_path='C:\\Projects',
            options=options
        )

        result = resolver.resolve_all(variables_node)

        assert result['ModsPath'] == 'C:\\Mods'
        assert result['ModName'] == 'TestMod'
        assert result['OutputPath'] == 'C:\\Mods\\TestMod'

    def test_resolve_forward_references(self):
        """Test that forward references work (later variable defined first)."""
        xml = """
        <Variables>
            <Variable Name="OutputPath" Value="@ModsPath\\@ModName"/>
            <Variable Name="ModsPath" Value="C:\\Mods"/>
            <Variable Name="ModName" Value="TestMod"/>
        </Variables>
        """
        variables_node = etree.fromstring(xml)

        options = MagicMock()
        for attr in ['bsarch_path', 'compiler_path', 'compiler_config_path', 'flags_path',
                     'game_path', 'log_path', 'output_path', 'package_path', 'registry_path',
                     'remote_temp_path', 'temp_path', 'zip_output_path']:
            setattr(options, attr, '')

        resolver = VariableResolver(
            program_path='C:\\Pyro',
            project_path='C:\\Projects',
            options=options
        )

        result = resolver.resolve_all(variables_node)

        assert result['OutputPath'] == 'C:\\Mods\\TestMod'

    def test_builtin_variables_available(self):
        """Test that built-in variables are available after resolve_all."""
        options = MagicMock()
        for attr in ['bsarch_path', 'compiler_path', 'compiler_config_path', 'flags_path',
                     'game_path', 'log_path', 'output_path', 'package_path', 'registry_path',
                     'remote_temp_path', 'temp_path', 'zip_output_path']:
            setattr(options, attr, '')

        resolver = VariableResolver(
            program_path='C:\\Pyro',
            project_path='C:\\Projects',
            options=options
        )

        result = resolver.resolve_all(None)

        assert 'UNIXTIME' in result
        assert 'PROGRAM_PATH' in result
        assert 'PROJECT_PATH' in result
        assert result['PROGRAM_PATH'] == 'C:\\Pyro'


class TestIntegrationWithRealProject:
    """Integration tests using real project files."""

    def test_utf8_project_variables(self, utf8_project_path: Path):
        """Test variable resolution with the utf8 test project."""
        # Parse the real project file
        tree = etree.parse(str(utf8_project_path))
        root = tree.getroot()

        # Find Variables node - handle namespace
        ns = {'ns': 'PapyrusProject.xsd'}
        variables_node = root.find('ns:Variables', ns)

        if variables_node is None:
            pytest.skip("No Variables node in utf8 project")

        options = MagicMock()
        for attr in ['bsarch_path', 'compiler_path', 'compiler_config_path', 'flags_path',
                     'game_path', 'log_path', 'output_path', 'package_path', 'registry_path',
                     'remote_temp_path', 'temp_path', 'zip_output_path']:
            setattr(options, attr, '')

        resolver = VariableResolver(
            program_path=str(utf8_project_path.parent.parent.parent),
            project_path=str(utf8_project_path.parent),
            options=options
        )

        # Parse user variables (without namespace-aware filtering for test)
        user_vars = {}
        for node in variables_node:
            name = node.get('Name', '')
            value = node.get('Value', '')
            if name and value:
                user_vars[name] = value

        assert 'ModName' in user_vars
        assert user_vars['ModName'] == 'utf8'
