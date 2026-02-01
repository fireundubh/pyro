from lxml import etree


class XmlRoot:
    node: etree.ElementBase
    ns: str = ''

    def __init__(self, element_tree: etree._ElementTree[etree._Element]) -> None:
        self.node = element_tree.getroot()

        nsmap, prefix = self.node.nsmap, self.node.prefix
        self.ns = nsmap[prefix] if prefix in nsmap else ''

    def find(self, key: str) -> etree._Element | None:
        path = key if not self.ns else f'ns:{key}', {'ns': self.ns}
        return self.node.find(*path)

    def get(self, key: str, default: str | None = None) -> str | None:
        result = self.node.get(key, default)
        return str(result) if result is not None else default
