import io
import os
import re
import typing

from lxml import etree


class XmlHelper:
    @staticmethod
    def strip_xml_comments(path: str) -> io.StringIO:
        with open(path, encoding='utf-8') as f:
            xml_document: str = f.read()
            comments_pattern = re.compile('(<!--.*?-->)', flags=re.DOTALL)
            xml_document = comments_pattern.sub('', xml_document)
        return io.StringIO(xml_document)

    @staticmethod
    def validate_schema(namespace: str, program_path: str) -> typing.Optional[etree.XMLSchema]:
        if not namespace:
            return None

        schema_path = os.path.join(program_path, namespace)
        if not os.path.isfile(schema_path):
            raise FileExistsError('Schema file does not exist: "%s"' % schema_path)

        schema = etree.parse(schema_path)
        return etree.XMLSchema(schema)
