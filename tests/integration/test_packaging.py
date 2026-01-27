"""
Integration tests for PackagingService and ZipService.
Tests verify service behavior and data tracking.
"""
from decimal import Decimal

import pytest

from pyro.services.PackagingService import PackageData, PackagingService
from pyro.services.ZipService import ZippingData, ZipService


class TestPackageData:
    """Test PackageData dataclass."""

    def test_initial_values(self):
        """Test default initialization values."""
        data = PackageData()

        assert data.file_count == 0
        assert data.time.start_time == 0.0
        assert data.time.end_time == 0.0

    def test_to_string_format(self):
        """Test to_string produces expected format."""
        data = PackageData()
        data.file_count = 25
        data.time.start_time = 100.0
        data.time.end_time = 105.0

        result = data.to_string()

        assert 'Package time:' in result
        assert '25 files' in result

    def test_time_tracking(self):
        """Test time tracking functionality."""
        import time

        data = PackageData()
        data.time.start_time = time.time()
        time.sleep(0.01)
        data.time.end_time = time.time()

        elapsed = data.time.value()

        assert elapsed > Decimal('0')
        assert elapsed < Decimal('1')


class TestZippingData:
    """Test ZippingData dataclass."""

    def test_initial_values(self):
        """Test default initialization values."""
        data = ZippingData()

        assert data.file_count == 0
        assert data.time.start_time == 0.0
        assert data.time.end_time == 0.0

    def test_to_string_format(self):
        """Test to_string produces expected format."""
        data = ZippingData()
        data.file_count = 10
        data.time.start_time = 100.0
        data.time.end_time = 102.5

        result = data.to_string()

        assert 'Zipping time:' in result
        assert '10 files' in result

    def test_time_tracking(self):
        """Test time tracking functionality."""
        import time

        data = ZippingData()
        data.time.start_time = time.time()
        time.sleep(0.01)
        data.time.end_time = time.time()

        elapsed = data.time.value()

        assert elapsed > Decimal('0')
        assert elapsed < Decimal('1')


class TestPackagingService:
    """Test PackagingService class."""

    def test_initialization(self):
        """Test service initialization creates package data."""
        class MockPpj:
            pass

        service = PackagingService(MockPpj())

        assert service.package_data is not None
        assert isinstance(service.package_data, PackageData)

    def test_multiple_services_independent(self):
        """Test that multiple service instances have independent data."""
        class MockPpj:
            pass

        service1 = PackagingService(MockPpj())
        service2 = PackagingService(MockPpj())

        service1.package_data.file_count = 50

        assert service2.package_data.file_count == 0


class TestZipService:
    """Test ZipService class."""

    def test_initialization(self):
        """Test service initialization creates zipping data."""
        class MockPpj:
            pass

        service = ZipService(MockPpj())

        assert service.zipping_data is not None
        assert isinstance(service.zipping_data, ZippingData)

    def test_multiple_services_independent(self):
        """Test that multiple service instances have independent data."""
        class MockPpj:
            pass

        service1 = ZipService(MockPpj())
        service2 = ZipService(MockPpj())

        service1.zipping_data.file_count = 30

        assert service2.zipping_data.file_count == 0
