import os
import typing

from lxml import etree

from pyro.Logger import Logger


class ElementHelper(Logger):
    @staticmethod
    def validate_schema(parent_element: etree.ElementBase, program_path: str) -> typing.Optional[etree.XMLSchema]:
        namespace = parent_element.nsmap[parent_element.prefix]

        if namespace:
            schema_path = os.path.join(program_path, namespace)

            if os.path.isfile(schema_path):
                schema = etree.parse(schema_path)
                return etree.XMLSchema(schema)

        return None

    @staticmethod
    def get(parent_element: etree.ElementBase, tag: str) -> etree.ElementBase:
        namespace = parent_element.nsmap[parent_element.prefix]
        return parent_element.find(tag) if not namespace else parent_element.find('ns:%s' % tag, {'ns': '%s' % namespace})
