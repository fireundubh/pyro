class CommandArguments:
    def __init__(self) -> None:
        self._items: list[str] = []

    @staticmethod
    def _needs_quoting(value: str) -> bool:
        """Check if a value needs quoting (contains spaces or special chars)."""
        return ' ' in value or '\t' in value

    @staticmethod
    def _quote_if_needed(value: str, force: bool = False) -> str:
        """Add quotes around value if it contains spaces or force is True."""
        if force or CommandArguments._needs_quoting(value):
            # Only add quotes if not already quoted
            if not (value.startswith('"') and value.endswith('"')):
                return f'"{value}"'
        return value

    def append(self, value: str, *, key: str = '', enquote_value: bool = False) -> None:
        """
        Append a command argument.

        Args:
            value: The argument value
            key: Optional key for key=value arguments (without leading dash)
            enquote_value: If True, force quoting even if no spaces present
        """
        if key:
            # For key=value arguments, quote the value part if needed
            quoted_value = self._quote_if_needed(value, force=enquote_value)
            self._items.append(f'-{key}={quoted_value}')
        else:
            # For standalone arguments, quote if needed
            quoted_value = self._quote_if_needed(value, force=enquote_value)
            self._items.append(quoted_value)

    def clear(self) -> None:
        self._items.clear()

    def to_list(self) -> list[str]:
        """Return the command arguments as a list suitable for subprocess."""
        return self._items.copy()

    def join(self, delimiter: str = ' ') -> str:
        """Deprecated: Returns space-joined string for backward compatibility."""
        return delimiter.join(self._items)
