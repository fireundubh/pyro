class ZipCompression:
    STORE = 0
    DEFLATE = 8
    MAP = {'STORE': 0, 'DEFLATE': 8}

    @staticmethod
    def get(value: str) -> int:
        try:
            return ZipCompression.MAP[value.upper()]
        except KeyError:
            pass

        raise ValueError("%s is not a valid key" % value.upper())
