from dataclasses import (dataclass,
                         field)

from pyro.TimeElapsed import TimeElapsed


@dataclass
class PackageData:
    time: TimeElapsed = field(init=False, default_factory=TimeElapsed)
    file_count: int = field(init=False, default_factory=int)

    def __post_init__(self):
        self.time = TimeElapsed()

    def to_string(self):
        raw_time, avg_time = ('{0:.3f}s'.format(t)
                              for t in (self.time.value(), self.time.average(self.file_count)))

        return f'Package time: ' \
               f'{raw_time} ({avg_time}/file, {self.file_count} files)'
