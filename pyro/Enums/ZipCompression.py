from enum import Enum


class ZipCompression(Enum):
    STORE = 0
    DEFLATE = 8

    @classmethod
    def _missing_(cls, value):
        try:
            return cls[value.upper()]
        except KeyError:
            pass

        raise ValueError("%r is not a valid %s" % (value, cls.__name__))
