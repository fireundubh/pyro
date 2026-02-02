"""
Integration tests for new compiler abstraction layer.

Tests the pyro.compilers module including StandardCompiler and CapricaCompiler.
"""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pyro.Constants import GameType
from pyro.compilers import create_compiler, StandardCompiler, CapricaCompiler
from pyro.compilers.protocol import CompilationContext, CompilationResult


class TestCompilerFactory:
    """Test compiler factory function."""

    def test_create_standard_compiler(self):
        """Test creating standard compiler."""
        compiler = create_compiler('C:\\Compiler\\PapyrusCompiler.exe')

        assert isinstance(compiler, StandardCompiler)
        assert compiler.compiler_path == 'C:\\Compiler\\PapyrusCompiler.exe'

    def test_create_caprica_compiler(self):
        """Test creating Caprica compiler."""
        compiler = create_compiler('C:\\Tools\\Caprica.exe', 'C:\\Tools\\caprica.cfg')

        assert isinstance(compiler, CapricaCompiler)
        assert compiler.compiler_path == 'C:\\Tools\\Caprica.exe'
        assert compiler.config_path == 'C:\\Tools\\caprica.cfg'

    def test_create_caprica_case_insensitive(self):
        """Test that Caprica detection is case insensitive."""
        compiler = create_compiler('C:\\Tools\\CAPRICA.EXE', 'C:\\Tools\\caprica.cfg')

        assert isinstance(compiler, CapricaCompiler)

    def test_exact_filename_match(self):
        """Test that factory uses exact filename match, not endswith."""
        # File ending with 'caprica.exe' but not exactly 'caprica.exe'
        compiler = create_compiler('C:\\Tools\\mycaprica.exe')

        # Should be StandardCompiler because filename is 'mycaprica.exe', not 'caprica.exe'
        assert isinstance(compiler, StandardCompiler)


class TestStandardCompiler:
    """Test StandardCompiler implementation."""

    def test_build_commands_single_script_sse(self):
        """Test building command for a single SSE script."""
        compiler = StandardCompiler('C:\\Compiler\\PapyrusCompiler.exe')

        context = CompilationContext(
            psc_paths={'TestScript': 'C:\\Source\\TestScript.psc'},
            import_paths=['C:\\Source', 'C:\\SkyrimSource'],
            flags_path='TESV_Papyrus_Flags.flg',
            output_path='C:\\Output',
            game_type=GameType.SSE,
            release=False,
            final=False,
            optimize=False,
            debug=False,
            quiet=False,
            asm='none',
            no_parallel=False,
            worker_limit=4
        )

        result = compiler.build_commands(context)

        assert isinstance(result, CompilationResult)
        assert result.command_count == 1
        assert len(result.commands) == 1
        assert result.is_batch is False

        command = result.commands[0]
        assert 'C:\\Compiler\\PapyrusCompiler.exe' in command
        assert 'C:\\Source\\TestScript.psc' in command
        assert any('-f=' in arg for arg in command)
        assert any('-i=' in arg for arg in command)
        assert any('-o=' in arg for arg in command)

    def test_build_commands_multiple_scripts(self):
        """Test building commands for multiple scripts."""
        compiler = StandardCompiler('C:\\Compiler\\PapyrusCompiler.exe')

        context = CompilationContext(
            psc_paths={
                'Script1': 'C:\\Source\\Script1.psc',
                'Script2': 'C:\\Source\\Script2.psc',
                'Script3': 'C:\\Source\\Script3.psc',
            },
            import_paths=['C:\\Source'],
            flags_path='TESV_Papyrus_Flags.flg',
            output_path='C:\\Output',
            game_type=GameType.SSE,
            release=False,
            final=False,
            optimize=False,
            debug=False,
            quiet=False,
            asm='none',
            no_parallel=False,
            worker_limit=4
        )

        result = compiler.build_commands(context)

        assert result.command_count == 3
        assert len(result.commands) == 3
        assert result.is_batch is False

    def test_build_commands_fo4_uses_colons(self):
        """Test that FO4 uses colon-separated object names."""
        compiler = StandardCompiler('C:\\Compiler\\PapyrusCompiler.exe')

        context = CompilationContext(
            psc_paths={'Scripts/Namespace/Script.psc': 'C:\\Source\\Scripts\\Namespace\\Script.psc'},
            import_paths=['C:\\Source'],
            flags_path='Institute_Papyrus_Flags.flg',
            output_path='C:\\Output',
            game_type=GameType.FO4,
            release=False,
            final=False,
            optimize=False,
            debug=False,
            quiet=False,
            asm='none',
            no_parallel=False,
            worker_limit=4
        )

        result = compiler.build_commands(context)

        command = result.commands[0]
        # Should use formatted object name with colons, not path
        assert 'Scripts:Namespace:Script' in command
        assert 'Script.psc' not in ' '.join(command)

    def test_build_commands_sf1_uses_colons(self):
        """Test that SF1 uses colon-separated object names."""
        compiler = StandardCompiler('C:\\Compiler\\PapyrusCompiler.exe')

        context = CompilationContext(
            psc_paths={'Scripts/MyMod/Player.psc': 'C:\\Source\\Scripts\\MyMod\\Player.psc'},
            import_paths=['C:\\Source'],
            flags_path='Starfield_Papyrus_Flags.flg',
            output_path='C:\\Output',
            game_type=GameType.SF1,
            release=False,
            final=False,
            optimize=False,
            debug=False,
            quiet=False,
            asm='none',
            no_parallel=False,
            worker_limit=4
        )

        result = compiler.build_commands(context)

        command = result.commands[0]
        # Should use formatted object name with colons
        assert 'Scripts:MyMod:Player' in command

    def test_build_commands_empty_scripts(self):
        """Test handling of empty script list."""
        compiler = StandardCompiler('C:\\Compiler\\PapyrusCompiler.exe')

        context = CompilationContext(
            psc_paths={},
            import_paths=['C:\\Source'],
            flags_path='TESV_Papyrus_Flags.flg',
            output_path='C:\\Output',
            game_type=GameType.SSE,
            release=False,
            final=False,
            optimize=False,
            debug=False,
            quiet=False,
            asm='none',
            no_parallel=False,
            worker_limit=4
        )

        result = compiler.build_commands(context)

        assert result.command_count == 0
        assert result.commands == []
        assert result.is_batch is False

    def test_fo4_release_flag(self):
        """Test that FO4 release flag is added."""
        compiler = StandardCompiler('C:\\Compiler\\PapyrusCompiler.exe')

        context = CompilationContext(
            psc_paths={'Script': 'C:\\Source\\Script.psc'},
            import_paths=['C:\\Source'],
            flags_path='Institute_Papyrus_Flags.flg',
            output_path='C:\\Output',
            game_type=GameType.FO4,
            release=True,
            final=False,
            optimize=False,
            debug=False,
            quiet=False,
            asm='none',
            no_parallel=False,
            worker_limit=4
        )

        result = compiler.build_commands(context)

        command = result.commands[0]
        assert '-release' in command

    def test_fo4_final_flag(self):
        """Test that FO4 final flag is added."""
        compiler = StandardCompiler('C:\\Compiler\\PapyrusCompiler.exe')

        context = CompilationContext(
            psc_paths={'Script': 'C:\\Source\\Script.psc'},
            import_paths=['C:\\Source'],
            flags_path='Institute_Papyrus_Flags.flg',
            output_path='C:\\Output',
            game_type=GameType.FO4,
            release=False,
            final=True,
            optimize=False,
            debug=False,
            quiet=False,
            asm='none',
            no_parallel=False,
            worker_limit=4
        )

        result = compiler.build_commands(context)

        command = result.commands[0]
        assert '-final' in command

    def test_optimize_flag(self):
        """Test that optimize flag is added."""
        compiler = StandardCompiler('C:\\Compiler\\PapyrusCompiler.exe')

        context = CompilationContext(
            psc_paths={'Script': 'C:\\Source\\Script.psc'},
            import_paths=['C:\\Source'],
            flags_path='TESV_Papyrus_Flags.flg',
            output_path='C:\\Output',
            game_type=GameType.SSE,
            release=False,
            final=False,
            optimize=True,
            debug=False,
            quiet=False,
            asm='none',
            no_parallel=False,
            worker_limit=4
        )

        result = compiler.build_commands(context)

        command = result.commands[0]
        assert '-op' in command

    def test_debug_flag(self):
        """Test that debug flag is added."""
        compiler = StandardCompiler('C:\\Compiler\\PapyrusCompiler.exe')

        context = CompilationContext(
            psc_paths={'Script': 'C:\\Source\\Script.psc'},
            import_paths=['C:\\Source'],
            flags_path='TESV_Papyrus_Flags.flg',
            output_path='C:\\Output',
            game_type=GameType.SSE,
            release=False,
            final=False,
            optimize=False,
            debug=True,
            quiet=False,
            asm='none',
            no_parallel=False,
            worker_limit=4
        )

        result = compiler.build_commands(context)

        command = result.commands[0]
        assert '-debug' in command

    def test_quiet_flag(self):
        """Test that quiet flag is added."""
        compiler = StandardCompiler('C:\\Compiler\\PapyrusCompiler.exe')

        context = CompilationContext(
            psc_paths={'Script': 'C:\\Source\\Script.psc'},
            import_paths=['C:\\Source'],
            flags_path='TESV_Papyrus_Flags.flg',
            output_path='C:\\Output',
            game_type=GameType.SSE,
            release=False,
            final=False,
            optimize=False,
            debug=False,
            quiet=True,
            asm='none',
            no_parallel=False,
            worker_limit=4
        )

        result = compiler.build_commands(context)

        command = result.commands[0]
        assert '-quiet' in command

    def test_asm_keep_flag(self):
        """Test that asm keep flag is added."""
        compiler = StandardCompiler('C:\\Compiler\\PapyrusCompiler.exe')

        context = CompilationContext(
            psc_paths={'Script': 'C:\\Source\\Script.psc'},
            import_paths=['C:\\Source'],
            flags_path='TESV_Papyrus_Flags.flg',
            output_path='C:\\Output',
            game_type=GameType.SSE,
            release=False,
            final=False,
            optimize=False,
            debug=False,
            quiet=False,
            asm='keep',
            no_parallel=False,
            worker_limit=4
        )

        result = compiler.build_commands(context)

        command = result.commands[0]
        assert '-keepasm' in command

    def test_asm_only_flag(self):
        """Test that asm only flag is added."""
        compiler = StandardCompiler('C:\\Compiler\\PapyrusCompiler.exe')

        context = CompilationContext(
            psc_paths={'Script': 'C:\\Source\\Script.psc'},
            import_paths=['C:\\Source'],
            flags_path='TESV_Papyrus_Flags.flg',
            output_path='C:\\Output',
            game_type=GameType.SSE,
            release=False,
            final=False,
            optimize=False,
            debug=False,
            quiet=False,
            asm='only',
            no_parallel=False,
            worker_limit=4
        )

        result = compiler.build_commands(context)

        command = result.commands[0]
        assert '-asmonly' in command

    def test_asm_discard_flag(self):
        """Test that asm discard flag is added."""
        compiler = StandardCompiler('C:\\Compiler\\PapyrusCompiler.exe')

        context = CompilationContext(
            psc_paths={'Script': 'C:\\Source\\Script.psc'},
            import_paths=['C:\\Source'],
            flags_path='TESV_Papyrus_Flags.flg',
            output_path='C:\\Output',
            game_type=GameType.SSE,
            release=False,
            final=False,
            optimize=False,
            debug=False,
            quiet=False,
            asm='discard',
            no_parallel=False,
            worker_limit=4
        )

        result = compiler.build_commands(context)

        command = result.commands[0]
        assert '-noasm' in command

    def test_supports_parallel_execution(self):
        """Test that standard compiler supports parallel execution."""
        compiler = StandardCompiler('C:\\Compiler\\PapyrusCompiler.exe')

        context = CompilationContext(
            psc_paths={'Script': 'C:\\Source\\Script.psc'},
            import_paths=['C:\\Source'],
            flags_path='TESV_Papyrus_Flags.flg',
            output_path='C:\\Output',
            game_type=GameType.SSE,
            release=False,
            final=False,
            optimize=False,
            debug=False,
            quiet=False,
            asm='none',
            no_parallel=False,
            worker_limit=4
        )

        assert compiler.supports_parallel_execution(context) is True

    def test_no_parallel_disables_parallel(self):
        """Test that no_parallel flag disables parallel execution."""
        compiler = StandardCompiler('C:\\Compiler\\PapyrusCompiler.exe')

        context = CompilationContext(
            psc_paths={'Script': 'C:\\Source\\Script.psc'},
            import_paths=['C:\\Source'],
            flags_path='TESV_Papyrus_Flags.flg',
            output_path='C:\\Output',
            game_type=GameType.SSE,
            release=False,
            final=False,
            optimize=False,
            debug=False,
            quiet=False,
            asm='none',
            no_parallel=True,
            worker_limit=4
        )

        assert compiler.supports_parallel_execution(context) is False

    def test_get_success_model(self):
        """Test that standard compiler uses per-script success model."""
        compiler = StandardCompiler('C:\\Compiler\\PapyrusCompiler.exe')

        assert compiler.get_success_model() == 'per-script'


class TestCapricaCompiler:
    """Test CapricaCompiler implementation."""

    def test_build_commands_single_batch(self):
        """Test that Caprica creates a single batch command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'caprica.cfg'
            config_path.write_text('parallel-compile=1\n', encoding='utf-8')

            compiler = CapricaCompiler('C:\\Tools\\Caprica.exe', str(config_path))

            context = CompilationContext(
                psc_paths={
                    'Script1': 'C:\\Source\\Script1.psc',
                    'Script2': 'C:\\Source\\Script2.psc',
                    'Script3': 'C:\\Source\\Script3.psc',
                },
                import_paths=['C:\\Source'],
                flags_path='TESV_Papyrus_Flags.flg',
                output_path='C:\\Output',
                game_type=GameType.SSE,
                release=False,
                final=False,
                optimize=False,
                debug=False,
                quiet=False,
                asm='none',
                no_parallel=False,
                worker_limit=4
            )

            result = compiler.build_commands(context)

            assert result.command_count == 3  # 3 scripts
            assert len(result.commands) == 1  # But only 1 command
            assert result.is_batch is True

            command = result.commands[0]
            assert 'C:\\Tools\\Caprica.exe' in command
            assert any('-config-file=' in arg for arg in command)
            assert any('-g=' in arg for arg in command)
            assert any('-f=' in arg for arg in command)
            assert any('-i=' in arg for arg in command)
            assert any('-o=' in arg for arg in command)

    def test_build_commands_empty_scripts(self):
        """Test handling of empty script list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'caprica.cfg'
            config_path.write_text('parallel-compile=1\n', encoding='utf-8')

            compiler = CapricaCompiler('C:\\Tools\\Caprica.exe', str(config_path))

            context = CompilationContext(
                psc_paths={},
                import_paths=['C:\\Source'],
                flags_path='TESV_Papyrus_Flags.flg',
                output_path='C:\\Output',
                game_type=GameType.SSE,
                release=False,
                final=False,
                optimize=False,
                debug=False,
                quiet=False,
                asm='none',
                no_parallel=False,
                worker_limit=4
            )

            result = compiler.build_commands(context)

            assert result.command_count == 0
            assert result.commands == []
            assert result.is_batch is True

    def test_game_name_fo4(self):
        """Test that FO4 uses 'fallout4' game name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'caprica.cfg'
            config_path.write_text('parallel-compile=1\n', encoding='utf-8')

            compiler = CapricaCompiler('C:\\Tools\\Caprica.exe', str(config_path))

            context = CompilationContext(
                psc_paths={'Script': 'C:\\Source\\Script.psc'},
                import_paths=['C:\\Source'],
                flags_path='Institute_Papyrus_Flags.flg',
                output_path='C:\\Output',
                game_type=GameType.FO4,
                release=False,
                final=False,
                optimize=False,
                debug=False,
                quiet=False,
                asm='none',
                no_parallel=False,
                worker_limit=4
            )

            result = compiler.build_commands(context)

            command = result.commands[0]
            assert any('-g=fallout4' in arg for arg in command)

    def test_game_name_sse(self):
        """Test that SSE uses 'skyrim' game name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'caprica.cfg'
            config_path.write_text('parallel-compile=1\n', encoding='utf-8')

            compiler = CapricaCompiler('C:\\Tools\\Caprica.exe', str(config_path))

            context = CompilationContext(
                psc_paths={'Script': 'C:\\Source\\Script.psc'},
                import_paths=['C:\\Source'],
                flags_path='TESV_Papyrus_Flags.flg',
                output_path='C:\\Output',
                game_type=GameType.SSE,
                release=False,
                final=False,
                optimize=False,
                debug=False,
                quiet=False,
                asm='none',
                no_parallel=False,
                worker_limit=4
            )

            result = compiler.build_commands(context)

            command = result.commands[0]
            assert any('-g=skyrim' in arg for arg in command)

    def test_game_name_tes5(self):
        """Test that TES5 uses 'skyrim' game name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'caprica.cfg'
            config_path.write_text('parallel-compile=1\n', encoding='utf-8')

            compiler = CapricaCompiler('C:\\Tools\\Caprica.exe', str(config_path))

            context = CompilationContext(
                psc_paths={'Script': 'C:\\Source\\Script.psc'},
                import_paths=['C:\\Source'],
                flags_path='TESV_Papyrus_Flags.flg',
                output_path='C:\\Output',
                game_type=GameType.TES5,
                release=False,
                final=False,
                optimize=False,
                debug=False,
                quiet=False,
                asm='none',
                no_parallel=False,
                worker_limit=4
            )

            result = compiler.build_commands(context)

            command = result.commands[0]
            assert any('-g=skyrim' in arg for arg in command)

    def test_game_name_sf1(self):
        """Test that SF1 uses 'starfield' game name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'caprica.cfg'
            config_path.write_text('parallel-compile=1\n', encoding='utf-8')

            compiler = CapricaCompiler('C:\\Tools\\Caprica.exe', str(config_path))

            context = CompilationContext(
                psc_paths={'Script': 'C:\\Source\\Script.psc'},
                import_paths=['C:\\Source'],
                flags_path='Starfield_Papyrus_Flags.flg',
                output_path='C:\\Output',
                game_type=GameType.SF1,
                release=False,
                final=False,
                optimize=False,
                debug=False,
                quiet=False,
                asm='none',
                no_parallel=False,
                worker_limit=4
            )

            result = compiler.build_commands(context)

            command = result.commands[0]
            assert any('-g=starfield' in arg for arg in command)

    def test_no_parallel_disables_config(self):
        """Test that no_parallel removes parallel-compile from config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'caprica.cfg'
            config_path.write_text('parallel-compile=1\nother-option=value\n', encoding='utf-8')

            compiler = CapricaCompiler('C:\\Tools\\Caprica.exe', str(config_path))

            context = CompilationContext(
                psc_paths={'Script': 'C:\\Source\\Script.psc'},
                import_paths=['C:\\Source'],
                flags_path='TESV_Papyrus_Flags.flg',
                output_path='C:\\Output',
                game_type=GameType.SSE,
                release=False,
                final=False,
                optimize=False,
                debug=False,
                quiet=False,
                asm='none',
                no_parallel=True,
                worker_limit=4
            )

            result = compiler.build_commands(context)

            # Verify config file was created
            command = result.commands[0]
            config_arg = [arg for arg in command if '-config-file=' in arg][0]
            created_config = config_arg.split('=', 1)[1].strip('"')

            # Read the created config file
            created_config_content = Path(created_config).read_text(encoding='utf-8')

            # parallel-compile should be removed
            assert 'parallel-compile' not in created_config_content
            # Other options should still be there
            assert 'other-option=value' in created_config_content

    def test_command_line_limit_uses_config_file(self):
        """Test that large script lists use config file for input."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'caprica.cfg'
            config_path.write_text('parallel-compile=1\n', encoding='utf-8')

            compiler = CapricaCompiler('C:\\Tools\\Caprica.exe', str(config_path))

            # Create a large script list that exceeds 32486 chars
            large_psc_paths = {}
            for i in range(1000):
                name = f'Scripts/VeryLongNamespace/VeryLongModName/Script{i}'
                large_psc_paths[name] = f'C:\\Source\\{name}.psc'

            context = CompilationContext(
                psc_paths=large_psc_paths,
                import_paths=['C:\\Source'],
                flags_path='TESV_Papyrus_Flags.flg',
                output_path='C:\\Output',
                game_type=GameType.SSE,
                release=False,
                final=False,
                optimize=False,
                debug=False,
                quiet=False,
                asm='none',
                no_parallel=False,
                worker_limit=4
            )

            result = compiler.build_commands(context)

            command = result.commands[0]

            # When using config file for input, the command line shouldn't contain all script names
            command_str = ' '.join(command)
            # Script names should not be in command line (they're in config file)
            assert 'Script999' not in command_str

            # Verify config file was created with input-file option
            config_arg = [arg for arg in command if '-config-file=' in arg][0]
            created_config = config_arg.split('=', 1)[1].strip('"')
            created_config_content = Path(created_config).read_text(encoding='utf-8')

            assert 'input-file=' in created_config_content

    def test_supports_parallel_execution(self):
        """Test that Caprica doesn't support parallel execution at command level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'caprica.cfg'
            config_path.write_text('parallel-compile=1\n', encoding='utf-8')

            compiler = CapricaCompiler('C:\\Tools\\Caprica.exe', str(config_path))

            context = CompilationContext(
                psc_paths={'Script': 'C:\\Source\\Script.psc'},
                import_paths=['C:\\Source'],
                flags_path='TESV_Papyrus_Flags.flg',
                output_path='C:\\Output',
                game_type=GameType.SSE,
                release=False,
                final=False,
                optimize=False,
                debug=False,
                quiet=False,
                asm='none',
                no_parallel=False,
                worker_limit=4
            )

            # Caprica always returns False (single batch command)
            assert compiler.supports_parallel_execution(context) is False

    def test_get_success_model(self):
        """Test that Caprica uses batch success model."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'caprica.cfg'
            config_path.write_text('parallel-compile=1\n', encoding='utf-8')

            compiler = CapricaCompiler('C:\\Tools\\Caprica.exe', str(config_path))

            assert compiler.get_success_model() == 'batch'
