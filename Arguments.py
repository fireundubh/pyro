class Arguments(list):
    def __init__(self):
        super(Arguments, self).__init__()

    def append_quoted(self, value, name=None):
        self.append('-%s="%s"' % (name, value) if name is not None else '"%s"' % value)

    def join(self, delimiter=' '):
        return delimiter.join(self)
