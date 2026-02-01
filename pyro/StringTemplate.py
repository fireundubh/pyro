import re as _re
from string import Template


class StringTemplate(Template):
    delimiter = '@'
    idpattern = r'[_a-z][_a-z0-9]*'
    flags = _re.IGNORECASE | _re.ASCII
