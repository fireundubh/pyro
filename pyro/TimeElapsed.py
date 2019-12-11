from decimal import Context, Decimal, ROUND_DOWN


class TimeElapsed:
    start_time: float = 0.0
    end_time: float = 0.0

    def __init__(self) -> None:
        self._context = Context(prec=4, rounding=ROUND_DOWN)
        self.start_time = 0.0
        self.end_time = 0.0

    def average(self, dividend: int) -> Decimal:
        if dividend == 0:
            return round(Decimal(0), 3)
        value = self.value()
        if value.compare(0) == 0:
            return round(Decimal(0), 3)
        return round(Decimal(dividend, self._context) / value, 3)

    def value(self) -> Decimal:
        return Decimal(self.end_time) - Decimal(self.start_time)
