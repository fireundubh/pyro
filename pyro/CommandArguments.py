class CommandArguments(list):
    def __init__(self) -> None:
        super(CommandArguments, self).__init__()

    def append_quoted(self, value: str, name: str = '') -> None:
        self.append('-%s="%s"' % (name, value) if name else '"%s"' % value)

    def join(self, delimiter: str = ' ') -> str:
        return delimiter.join(self)
