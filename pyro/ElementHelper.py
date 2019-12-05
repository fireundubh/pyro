from lxml import etree

from pyro.Logger import Logger


class ElementHelper(Logger):
    @staticmethod
    def get_namespace(parent_element: etree.ElementBase) -> str:
        nsmap = parent_element.nsmap
        prefix = parent_element.prefix
        return nsmap[prefix] if prefix in nsmap else ''

    @staticmethod
    def get_node(tag: str, parent_element: etree.ElementBase, namespace: str) -> etree.ElementBase:
        path = tag if not namespace else 'ns:%s' % tag, {'ns': '%s' % namespace}
        return parent_element.find(*path)
