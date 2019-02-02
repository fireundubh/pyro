class TimeElapsed:
    def __init__(self):
        self._start_time = 0.0
        self._end_time = 0.0

    def __repr__(self):
        return self._diff()

    def __str__(self):
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

    def print(self):
        print('[PYRO] Time elapsed:', str(self))
