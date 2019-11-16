from typing import Callable


class TimeElapsed:
    def __init__(self) -> None:
        self._start_time = 0.0
        self._end_time = 0.0

    def __repr__(self) -> str:
        return str(self._diff())

    def __str__(self) -> str:
        return '{0:.2f}s'.format(self._diff())

    def _diff(self) -> float:
        return float(self.end_time - self.start_time)

    @property
    def start_time(self) -> float:
        return self._start_time

    @start_time.setter
    def start_time(self, value: float) -> None:
        self._start_time = value

    @property
    def end_time(self) -> float:
        return self._end_time

    @end_time.setter
    def end_time(self, value: float) -> None:
        self._end_time = value

    def print(self, *, callback_func: Callable = None) -> None:
        if not callback_func:
            callback_func = print
        callback_func('Compilation time: %s' % self)
