from typing import Any

from lxml import etree


class XmlRoot:
    node: etree.ElementBase = None
    ns: str = ''

    def __init__(self, element_tree: etree.ElementTree) -> None:
        self.node = element_tree.getroot()
        
        nsmap, prefix = self.node.nsmap, self.node.prefix
        self.ns = nsmap[prefix] if prefix in nsmap else ''

    def find(self, key: str) -> etree.ElementBase:
        path = key if not self.ns else f'ns:{key}', {'ns': self.ns}
        return self.node.find(*path)

    # noinspection Mypy
    def get(self, key: str, default: Any = None) -> Any:
        return self.node.get(key, default)
