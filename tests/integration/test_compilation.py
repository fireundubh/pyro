"""
Integration tests for CompilationService.
Tests verify service behavior without actual compiler execution.
"""
from decimal import Decimal

import pytest

from pyro.services.CompilationService import (
    TimeElapsed,
    CompileData,
    CompileDataCaprica,
    CompilationService,
)


class TestTimeElapsed:
    """Test TimeElapsed tracking class."""

    def test_value_calculates_elapsed(self):
        """Test that value() calculates elapsed time correctly."""
        te = TimeElapsed()
        te.start_time = 100.0
        te.end_time = 105.5

        result = te.value()

        assert result == Decimal('5.5')

    def test_value_with_no_elapsed(self):
        """Test value() with zero elapsed time."""
        te = TimeElapsed()
        te.start_time = 100.0
        te.end_time = 100.0

        result = te.value()

        assert result == Decimal('0')

    def test_average_calculates_correctly(self):
        """Test average time per operation."""
        te = TimeElapsed()
        te.start_time = 100.0
        te.end_time = 110.0  # 10 seconds total

        result = te.average(5)  # 5 operations

        assert result == Decimal('2')

    def test_average_with_zero_dividend(self):
        """Test average with zero operations returns zero."""
        te = TimeElapsed()
        te.start_time = 100.0
        te.end_time = 110.0

        result = te.average(0)

        assert result == Decimal('0')

    def test_average_with_zero_elapsed(self):
        """Test average with zero elapsed time returns zero."""
        te = TimeElapsed()
        te.start_time = 100.0
        te.end_time = 100.0

        result = te.average(5)

        assert result == Decimal('0')


class TestCompileData:
    """Test CompileData dataclass."""

    def test_failed_count(self):
        """Test failed_count calculation."""
        data = CompileData()
        data.command_count = 10
        data.success_count = 7

        assert data.failed_count == 3

    def test_failed_count_all_success(self):
        """Test failed_count when all scripts succeed."""
        data = CompileData()
        data.command_count = 10
        data.success_count = 10

        assert data.failed_count == 0

    def test_failed_count_all_fail(self):
        """Test failed_count when all scripts fail."""
        data = CompileData()
        data.command_count = 10
        data.success_count = 0

        assert data.failed_count == 10

    def test_to_string_format(self):
        """Test to_string produces expected format."""
        data = CompileData()
        data.command_count = 10
        data.success_count = 8
        data.scripts_count = 10
        data.time.start_time = 100.0
        data.time.end_time = 110.0

        result = data.to_string()

        assert 'Compile time:' in result
        assert '8 succeeded' in result
        assert '2 failed' in result
        assert '10 scripts' in result


class TestCompileDataCaprica:
    """Test CompileDataCaprica dataclass."""

    def test_failed_count_success(self):
        """Test failed_count when Caprica succeeds."""
        data = CompileDataCaprica()
        data.success_count = 1

        assert data.failed_count == 0

    def test_failed_count_failure(self):
        """Test failed_count when Caprica fails."""
        data = CompileDataCaprica()
        data.success_count = 0

        assert data.failed_count == 1

    def test_to_string_format(self):
        """Test to_string produces expected format."""
        data = CompileDataCaprica()
        data.scripts_count = 62
        data.success_count = 1
        data.time.start_time = 100.0
        data.time.end_time = 115.0

        result = data.to_string()

        assert 'Compile time:' in result
        assert '62 scripts' in result


class TestCompilationService:
    """Test CompilationService class."""

    def test_get_compile_data_standard(self):
        """Test get_compile_data returns standard data for non-Caprica."""
        class MockPpj:
            def get_compiler_path(self):
                return 'C:\\Skyrim\\PapyrusCompiler.exe'

        service = CompilationService(MockPpj())
        result = service.get_compile_data()

        assert isinstance(result, CompileData)
        assert not isinstance(result, CompileDataCaprica)

    def test_get_compile_data_caprica(self):
        """Test get_compile_data returns Caprica data for Caprica compiler."""
        class MockPpj:
            def get_compiler_path(self):
                return 'C:\\Tools\\Caprica.exe'

        service = CompilationService(MockPpj())
        result = service.get_compile_data()

        assert isinstance(result, CompileDataCaprica)

    def test_is_using_caprica_false(self):
        """Test is_using_caprica with standard compiler."""
        class MockPpj:
            def get_compiler_path(self):
                return 'C:\\Skyrim\\PapyrusCompiler.exe'

        service = CompilationService(MockPpj())

        assert not service.is_using_caprica()

    def test_is_using_caprica_true(self):
        """Test is_using_caprica with Caprica compiler."""
        class MockPpj:
            def get_compiler_path(self):
                return 'C:\\Tools\\Caprica.exe'

        service = CompilationService(MockPpj())

        assert service.is_using_caprica()

    def test_is_using_caprica_case_insensitive(self):
        """Test is_using_caprica is case-insensitive."""
        class MockPpj:
            def get_compiler_path(self):
                return 'C:\\Tools\\CAPRICA.EXE'

        service = CompilationService(MockPpj())

        assert service.is_using_caprica()


class TestCompilationServiceIntegration:
    """Integration tests using real project data structures."""

    def test_compile_data_tracks_timing(self):
        """Test that compile data properly tracks timing information."""
        data = CompileData()

        # Simulate compilation timing
        import time
        data.time.start_time = time.time()
        time.sleep(0.01)  # Small delay
        data.time.end_time = time.time()

        elapsed = data.time.value()

        assert elapsed > Decimal('0')
        assert elapsed < Decimal('1')  # Should be under 1 second

    def test_multiple_compile_data_instances_independent(self):
        """Test that multiple CompileData instances are independent."""
        data1 = CompileData()
        data2 = CompileData()

        data1.success_count = 5
        data1.command_count = 10

        # data2 should not be affected
        assert data2.success_count == 0
        assert data2.command_count == 0

    def test_compilation_service_instances_independent(self):
        """Test that CompilationService instances have independent data."""
        class MockPpj:
            def get_compiler_path(self):
                return 'C:\\PapyrusCompiler.exe'

        service1 = CompilationService(MockPpj())
        service2 = CompilationService(MockPpj())

        service1.compile_data.success_count = 10

        # service2 should not be affected
        assert service2.compile_data.success_count == 0
