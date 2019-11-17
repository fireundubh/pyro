class Logger:
    HEAD = '\033[95m'
    OKBL = '\033[94m'
    OKGR = '\033[92m'
    WARN = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDR = '\033[4m'

    def __init__(self) -> None:
        pass

    @staticmethod
    def error(message: str) -> int:
        print('{}[ERRO] {}{}'.format(Logger.FAIL, message, Logger.ENDC))
        return 1

    @staticmethod
    def warn(message: str) -> None:
        print('{}[WARN] {}{}'.format(Logger.WARN, message, Logger.ENDC))

    @staticmethod
    def bsarch(message: str) -> None:
        print('[BSAR] {}'.format(message))

    @staticmethod
    def compiler(message: str) -> None:
        print('[CMPL] {}'.format(message))

    @staticmethod
    def pyro(message: str) -> None:
        print('[PYRO] {}'.format(message))

    @staticmethod
    def anon(message: str) -> None:
        print('[ANON] {}'.format(message))
