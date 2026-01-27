"""
ZipService - Handles ZIP archive creation.

Extracted from BuildFacade.try_zip().
Thin wrapper around PackageManager with timing/stats tracking.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pyro.PackageManager import PackageManager
from pyro.services.CompilationService import TimeElapsed

if TYPE_CHECKING:
    from pyro.PapyrusProject import PapyrusProject


@dataclass
class ZippingData:
    """Tracks zipping statistics."""

    time: TimeElapsed = field(init=False, default_factory=TimeElapsed)
    file_count: int = field(init=False, default_factory=int)

    def __post_init__(self) -> None:
        self.time = TimeElapsed()

    def to_string(self) -> str:
        """Format zipping statistics as a string."""
        raw_time, avg_time = ('{0:.3f}s'.format(t)
                              for t in (self.time.value(), self.time.average(self.file_count)))

        return f'Zipping time: ' \
               f'{raw_time} ({avg_time}/file, {self.file_count} files)'


class ZipService:
    """Service for creating ZIP archives."""

    log: logging.Logger = logging.getLogger('pyro')

    def __init__(self, ppj: 'PapyrusProject') -> None:
        self.ppj = ppj
        self.zipping_data = ZippingData()

    def try_zip(self) -> None:
        """
        Create ZIP archive for the project.

        This is the main entry point, matching the original BuildFacade.try_zip() API.
        """
        self.zipping_data.time.start_time = time.time()
        package_manager = PackageManager(self.ppj)
        package_manager.create_zip()
        self.zipping_data.time.end_time = time.time()
        self.zipping_data.file_count = package_manager.includes
