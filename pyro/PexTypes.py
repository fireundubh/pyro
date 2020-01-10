class PexData:
    offset: int
    data: bytes
    value: object


class PexInt(PexData):
    value: int


class PexStr(PexData):
    value: str
