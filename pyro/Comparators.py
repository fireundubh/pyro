from typing import Union


def startswith(a_source: str, a_prefix: Union[str, tuple],
               a_start: int = None, a_end: int = None, /, ignorecase: bool = False) -> bool:

    source = a_source[a_start:a_end]

    prefixes = a_prefix if isinstance(a_prefix, tuple) else (a_prefix,)

    for prefix in prefixes:
        source_prefix = source[:len(prefix)]

        if not ignorecase:
            if source_prefix == prefix:
                return True
        else:
            if source_prefix.casefold() == prefix.casefold():
                return True

    return False


def endswith(a_source: str, a_suffix: Union[str, tuple],
             a_start: int = None, a_end: int = None, /, ignorecase: bool = False) -> bool:

    source = a_source[a_start:a_end]

    suffixes = a_suffix if isinstance(a_suffix, tuple) else (a_suffix,)

    for suffix in suffixes:
        source_suffix = source[-len(suffix):]

        if not ignorecase:
            if source_suffix == suffix:
                return True
        else:
            if source_suffix.casefold() == suffix.casefold():
                return True

    return False
