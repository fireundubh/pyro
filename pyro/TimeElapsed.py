from decimal import Context, Decimal, ROUND_DOWN


class TimeElapsed:
    def __init__(self) -> None:
        self._context = Context(prec=4, rounding=ROUND_DOWN)
        self.start_time: float = 0.0
        self.end_time: float = 0.0

    def average(self, dividend: int) -> Decimal:
        return round(Decimal(dividend, self._context) / self.value(), 3)

    def value(self) -> Decimal:
        return Decimal(self.end_time) - Decimal(self.start_time)
