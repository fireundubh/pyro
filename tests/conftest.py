"""
Shared pytest fixtures for integration tests.
Uses real project files from test_data/ - no mocks.
"""
import os
import shutil
import tempfile
from pathlib import Path
from typing import Generator

import pytest


# Get the repository root directory
REPO_ROOT = Path(__file__).parent.parent
TEST_DATA_DIR = REPO_ROOT / 'test_data'


@pytest.fixture
def test_data_dir() -> Path:
    """Returns the path to the test_data directory."""
    return TEST_DATA_DIR


@pytest.fixture
def utf8_project_path() -> Path:
    """Returns the path to the utf8 test project."""
    return TEST_DATA_DIR / 'utf8' / 'utf8.pyroproject'


@pytest.fixture
def campfire_project_path() -> Path:
    """Returns the path to the Campfire test project."""
    return TEST_DATA_DIR / 'Campfire' / 'Campfire.pyroproject'


@pytest.fixture
def handcart_project_path() -> Path:
    """Returns the path to the HandCart test project."""
    return TEST_DATA_DIR / 'HandCart' / 'HandCart.pyroproject'


@pytest.fixture
def fo4_autohelmet_project_path() -> Path:
    """Returns the path to the FO4 AutoHelmet test project."""
    return TEST_DATA_DIR / 'FO4_AutoHelmet' / 'AutoHelmet.pyroproject'


@pytest.fixture
def utf8_pex_paths() -> list[Path]:
    """Returns paths to all PEX files in the utf8 test project."""
    scripts_dir = TEST_DATA_DIR / 'utf8' / 'Scripts'
    return list(scripts_dir.glob('*.pex'))


@pytest.fixture
def utf8_non_anon_pex_paths() -> list[Path]:
    """Returns paths to non-anonymized PEX files in the utf8 test project."""
    scripts_dir = TEST_DATA_DIR / 'utf8' / 'Scripts'
    return [p for p in scripts_dir.glob('*.pex') if '_Anon' not in p.name]


@pytest.fixture
def utf8_anon_pex_paths() -> list[Path]:
    """Returns paths to already-anonymized PEX files in the utf8 test project."""
    scripts_dir = TEST_DATA_DIR / 'utf8' / 'Scripts'
    return [p for p in scripts_dir.glob('*_Anon.pex')]


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Creates a temporary directory for test outputs."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def temp_pex_copy(utf8_non_anon_pex_paths: list[Path], temp_dir: Path) -> Path:
    """Creates a temporary copy of a PEX file for testing modifications."""
    if not utf8_non_anon_pex_paths:
        pytest.skip("No non-anonymized PEX files found in utf8 test data")

    source = utf8_non_anon_pex_paths[0]
    dest = temp_dir / source.name
    shutil.copy2(source, dest)
    return dest


@pytest.fixture
def campfire_pex_paths() -> list[Path]:
    """Returns paths to all PEX files in the Campfire test project."""
    scripts_dir = TEST_DATA_DIR / 'Campfire' / 'Scripts'
    return list(scripts_dir.glob('*.pex'))


def create_minimal_options(input_path: str, **overrides):
    """
    Create a minimal ProjectOptions for testing.

    Args:
        input_path: Path to the project file
        **overrides: Any additional options to set
    """
    from pyro.ProjectOptions import ProjectOptions

    # Start with minimal required options
    options = ProjectOptions()
    options.input_path = input_path

    # Apply any overrides
    for key, value in overrides.items():
        setattr(options, key, value)

    return options


@pytest.fixture
def project_options_factory():
    """Factory fixture for creating ProjectOptions with custom settings."""
    return create_minimal_options
