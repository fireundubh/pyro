import re as _re
from string import Template


class StringTemplate(Template):
    # noinspection PyClassVar
    delimiter: str = '@'  # type: ignore
    idpattern = '([_a-z][_a-z0-9]*)'
    flags = _re.IGNORECASE | _re.ASCII
