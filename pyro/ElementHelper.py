import os
import sys

from lxml import etree

from pyro.Logger import Logger


class ElementHelper(Logger):
    @staticmethod
    def validate_schema(parent_element: etree.ElementBase, program_path: str) -> object:
        namespace = [ns for ns in parent_element.nsmap.values()]

        if namespace:
            schema_path = os.path.join(program_path, namespace[0])

            if os.path.exists(schema_path):
                schema = etree.parse(schema_path)
                return etree.XMLSchema(schema)

        return None

    @staticmethod
    def _get_children(parent_element: etree.ElementBase, tag: str) -> list:
        namespace = [ns for ns in parent_element.nsmap.values()]
        return parent_element.findall(tag[:-1]) if not namespace else parent_element.findall('ns:%s' % tag[:-1], {'ns': '%s' % namespace[0]})

    @staticmethod
    def get(parent_element: etree.ElementBase, tag: str) -> etree.ElementBase:
        namespace = [ns for ns in parent_element.nsmap.values()]
        return parent_element.find(tag) if not namespace else parent_element.find('ns:%s' % tag, {'ns': '%s' % namespace[0]})

    @staticmethod
    def get_child_values(parent_element: etree.ElementBase, tag: str) -> list:
        element: etree.ElementBase = ElementHelper.get(parent_element, tag)

        if element is None:
            ElementHelper.log.error('The PPJ file is missing the following tag: %s' % tag)
            sys.exit(1)

        children: list = ElementHelper._get_children(element, tag)

        if children is None or len(children) == 0:
            ElementHelper.log.error('No child elements exist for <%s> tag' % tag)
            sys.exit(1)

        return [str(child.text) for child in children if child.text is not None and child.text != '']
