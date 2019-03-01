class Logger:
    HEAD = '\033[95m'
    OKBL = '\033[94m'
    OKGR = '\033[92m'
    WARN = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDR = '\033[4m'

    def __init__(self):
        pass

    @staticmethod
    def error(message: str):
        print('{}[ERRO] {}{}'.format(Logger.FAIL, message, Logger.ENDC))
        return 1

    @staticmethod
    def warn(message: str):
        print('{}[WARN] {}{}'.format(Logger.WARN, message, Logger.ENDC))

    @staticmethod
    def bsarch(message: str):
        print('[BSAR] INFO: {}'.format(message))

    @staticmethod
    def compiler(message: str):
        print('[CMPL] {}'.format(message))

    @staticmethod
    def pyro(message: str):
        print('[PYRO] {}'.format(message))

    @staticmethod
    def idxr(message: str):
        print('[IDXR] {}'.format(message))

    @staticmethod
    def anon(message: str):
        print('[ANON] {}'.format(message))
