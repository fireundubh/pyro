"""
Integration tests for AnonymizationService.
Uses real PEX files from test_data/ - no mocks.
"""
import os
import shutil
from pathlib import Path

import pytest

from pyro.Exceptions import AnonymizationError
from pyro.PexReader import PexReader
from pyro.services.AnonymizationService import AnonymizationService


class TestPexHeaderReading:
    """Test reading PEX file headers."""

    def test_read_skyrim_pex_header(self, utf8_non_anon_pex_paths: list[Path]):
        """Test reading a Skyrim SE PEX file header."""
        if not utf8_non_anon_pex_paths:
            pytest.skip("No non-anonymized PEX files found")

        pex_path = utf8_non_anon_pex_paths[0]
        header = PexReader.get_header(str(pex_path))

        # Skyrim SE uses big-endian magic
        assert header.endianness == 'big'
        assert header.magic.value == 0xDEC057FA

        # Should have valid metadata
        assert header.script_path.value
        assert '.psc' in header.script_path.value.lower()
        assert header.user_name.value
        assert header.computer_name.value

    def test_read_already_anonymized_pex(self, utf8_anon_pex_paths: list[Path]):
        """Test reading an already-anonymized PEX file."""
        if not utf8_anon_pex_paths:
            pytest.skip("No anonymized PEX files found")

        pex_path = utf8_anon_pex_paths[0]
        header = PexReader.get_header(str(pex_path))

        # Anonymized files have their paths randomized (no .psc extension visible)
        # The script_path should be random characters
        assert header.script_path.value
        # An anonymized file should NOT contain ".psc" in the path
        assert '.psc' not in header.script_path.value.lower()


class TestAnonymizeScript:
    """Test script anonymization."""

    def test_anonymize_pex_file(self, temp_pex_copy: Path):
        """Test anonymizing a single PEX file."""
        # Read original header
        original_header = PexReader.get_header(str(temp_pex_copy))
        original_script_path = original_header.script_path.value
        original_user_name = original_header.user_name.value
        original_computer_name = original_header.computer_name.value

        # Verify it's not already anonymized
        assert '.psc' in original_script_path.lower()

        # Create a minimal mock ppj for the service
        class MockPpj:
            psc_paths = {}
            pex_paths = []
            missing_scripts = {}
            class options:
                no_incremental_build = False

        service = AnonymizationService(MockPpj())
        service.anonymize_script(str(temp_pex_copy))

        # Read anonymized header
        anon_header = PexReader.get_header(str(temp_pex_copy))

        # Verify metadata was randomized
        assert anon_header.script_path.value != original_script_path
        assert anon_header.user_name.value != original_user_name
        assert anon_header.computer_name.value != original_computer_name

        # Verify lengths are preserved (required for valid PEX)
        assert len(anon_header.script_path.value) == len(original_script_path)
        assert len(anon_header.user_name.value) == len(original_user_name)
        assert len(anon_header.computer_name.value) == len(original_computer_name)

        # Verify anonymized path no longer contains .psc
        assert '.psc' not in anon_header.script_path.value.lower()

    def test_already_anonymized_warns(self, utf8_anon_pex_paths: list[Path], temp_dir: Path, caplog):
        """Test that re-anonymizing an already-anonymized file logs a warning."""
        if not utf8_anon_pex_paths:
            pytest.skip("No anonymized PEX files found")

        # Copy an already-anonymized file
        source = utf8_anon_pex_paths[0]
        dest = temp_dir / source.name
        shutil.copy2(source, dest)

        class MockPpj:
            psc_paths = {}
            pex_paths = []
            missing_scripts = {}
            class options:
                no_incremental_build = False

        service = AnonymizationService(MockPpj())

        # Should warn but not raise
        with caplog.at_level('WARNING'):
            service.anonymize_script(str(dest))

        assert 'Cannot anonymize script again' in caplog.text

    def test_anonymize_nonexistent_file_raises(self, temp_dir: Path):
        """Test that anonymizing a non-existent file raises an error."""
        fake_path = temp_dir / 'nonexistent.pex'

        class MockPpj:
            psc_paths = {}
            pex_paths = []
            missing_scripts = {}
            class options:
                no_incremental_build = False

        service = AnonymizationService(MockPpj())

        with pytest.raises(AnonymizationError, match='Cannot locate file'):
            service.anonymize_all([str(fake_path)])


class TestFindModifiedScripts:
    """Test finding scripts that need re-anonymization."""

    def test_find_modified_scripts_returns_list(self, temp_dir: Path, utf8_non_anon_pex_paths: list[Path]):
        """Test that find_modified_scripts returns a list of paths."""
        if not utf8_non_anon_pex_paths:
            pytest.skip("No PEX files found")

        # Copy PEX files to temp
        scripts_dir = temp_dir / 'Scripts'
        scripts_dir.mkdir()

        pex_copies = []
        for pex_path in utf8_non_anon_pex_paths[:2]:
            dest = scripts_dir / pex_path.name
            shutil.copy2(pex_path, dest)
            pex_copies.append(str(dest))

        # Create matching PSC paths (simulated - just need filenames)
        psc_paths = {}
        for pex_path in pex_copies:
            name = os.path.splitext(os.path.basename(pex_path))[0]
            # Create a fake PSC file with an older timestamp
            psc_path = scripts_dir / f'{name}.psc'
            psc_path.write_text('scriptname test')
            # Set PSC modification time to be older than PEX
            old_time = os.path.getmtime(pex_path) - 1000
            os.utime(psc_path, (old_time, old_time))
            psc_paths[name] = str(psc_path)

        class MockPpj:
            pass

        mock_ppj = MockPpj()
        mock_ppj.psc_paths = psc_paths
        mock_ppj.pex_paths = pex_copies

        service = AnonymizationService(mock_ppj)
        modified = service.find_modified_scripts()

        # Since PSC is older than PEX, all PEX files should be "modified"
        assert isinstance(modified, list)
        assert len(modified) == len(pex_copies)


class TestRandomization:
    """Test the randomization helper."""

    def test_randomize_str_lowercase(self):
        """Test lowercase string generation."""
        class MockPpj:
            pass

        result = AnonymizationService._randomize_str(10, uppercase=False)

        assert len(result) == 10
        assert result.islower()
        assert result.isalpha()

    def test_randomize_str_uppercase(self):
        """Test uppercase string generation."""
        result = AnonymizationService._randomize_str(10, uppercase=True)

        assert len(result) == 10
        assert result.isupper()
        assert result.isalpha()

    def test_randomize_str_different_each_time(self):
        """Test that randomization produces different results."""
        results = [AnonymizationService._randomize_str(20) for _ in range(10)]

        # All results should be unique (statistically very unlikely to collide)
        assert len(set(results)) == 10
