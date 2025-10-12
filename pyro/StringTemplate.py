import re as _re
from string import Template


class StringTemplate(Template):
    # noinspection PyClassVar
    delimiter: str = '@'
    idpattern = r'([_a-z][_a-z0-9]*)'
    flags = _re.IGNORECASE | _re.ASCII
    pattern = rf'{_re.escape(delimiter)}(?P<named>{idpattern})'
