import sys

from lxml import etree

from pyro.Logger import Logger


class ElementHelper:
    log = Logger()

    @staticmethod
    def _get_children(parent_element: etree.ElementBase, tag: str, ns: str = 'PapyrusProject.xsd') -> list:
        return parent_element.findall('ns:%s' % tag[:-1], {'ns': '%s' % ns})

    @staticmethod
    def get(parent_element: etree.ElementBase, tag: str, ns: str = 'PapyrusProject.xsd') -> etree.ElementBase:
        return parent_element.find('ns:%s' % tag, {'ns': '%s' % ns})

    @staticmethod
    def get_child_values(parent_element: etree.ElementBase, tag: str) -> list:
        element: etree.ElementBase = ElementHelper.get(parent_element, tag)

        if element is None:
            sys.exit(ElementHelper.log.pyro('The PPJ file is missing the following tag: %s' % tag))

        children: list = ElementHelper._get_children(element, tag)

        if children is None or len(children) == 0:
            sys.exit(ElementHelper.log.pyro('No child elements exist for <%s> tag' % tag))

        return [str(child.text) for child in children if child.text is not None and child.text != '']
