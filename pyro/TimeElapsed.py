from decimal import Context, Decimal, ROUND_DOWN
from typing import Callable


class TimeElapsed:
    def __init__(self) -> None:
        context = Context(prec=4, rounding=ROUND_DOWN)
        self.start_time: Decimal = Decimal(0, context)
        self.end_time: Decimal = Decimal(0, context)

    def print(self, *, callback_func: Callable = None) -> None:
        if not callback_func:
            callback_func = print
        time = '{0:.3f}s'.format(self.end_time - self.start_time)
        callback_func('Compilation time: %s' % time)
