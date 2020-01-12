class CommandArguments:
    def __init__(self) -> None:
        self._items: list = []

    def append(self, value: str, *, key: str = '', enquote_value: bool = False) -> None:
        if enquote_value:
            self._items.append(f'-{key}="{value}"' if key else f'"{value}"')
        else:
            self._items.append(value)

    def clear(self) -> None:
        self._items.clear()

    def join(self, delimiter: str = ' ') -> str:
        return delimiter.join(self._items)
