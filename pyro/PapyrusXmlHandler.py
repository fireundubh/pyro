import io
import logging
import os
import re
import sys

from typing import Union

from lxml import etree

from pyro.Constants import (XmlAttributeName,
                            XmlTagName)
from pyro.XmlRoot import XmlRoot


def strip_xml_comments(path: str) -> io.StringIO:
    with open(path, encoding='utf-8') as f:
        xml_document: str = f.read()
        comments_pattern = re.compile('(<!--.*?-->)', flags=re.DOTALL)
        xml_document = comments_pattern.sub('', xml_document)
    return io.StringIO(xml_document)


def validate_schema(namespace: str, program_path: str) -> etree.XMLSchema:
    if not namespace:
        return etree.XMLSchema()

    schema_path = os.path.join(program_path, namespace)
    if not os.path.isfile(schema_path):
        raise FileExistsError(f'Schema file does not exist: "{schema_path}"')

    schema = etree.parse(schema_path)
    return etree.XMLSchema(schema)


class PapyrusXmlHandler:
    log: logging.Logger = logging.getLogger('pyro')
    variables_node: etree.ElementBase

    def __init__(self, input_path: str, program_path: str) -> None:
        xml_parser: etree.XMLParser = etree.XMLParser(remove_blank_text=True, remove_comments=True)

        xml_document: io.StringIO = strip_xml_comments(input_path)

        # noinspection PyTypeChecker
        project_xml: etree._ElementTree = etree.parse(xml_document, xml_parser)

        self.ppj_root: XmlRoot = XmlRoot(project_xml)

        schema: etree.XMLSchema = validate_schema(self.ppj_root.ns, program_path)

        if schema:
            try:
                schema.assertValid(project_xml)
            except etree.DocumentInvalid as e:
                self.log.error(f'Failed to validate XML Schema.{os.linesep}\t{e}')
                sys.exit(1)
            else:
                self.log.info('Successfully validated XML Schema.')

        self.imports_node: etree.ElementBase = self.ppj_root.find(XmlTagName.IMPORTS)
        self.scripts_node: etree.ElementBase = self.ppj_root.find(XmlTagName.SCRIPTS)
        self.folders_node: etree.ElementBase = self.ppj_root.find(XmlTagName.FOLDERS)
        self.packages_node: etree.ElementBase = self.ppj_root.find(XmlTagName.PACKAGES)
        self.zip_files_node: etree.ElementBase = self.ppj_root.find(XmlTagName.ZIP_FILES)

        self.pre_build_node: etree.ElementBase = self.ppj_root.find(XmlTagName.PRE_BUILD_EVENT)
        self.post_build_node: etree.ElementBase = self.ppj_root.find(XmlTagName.POST_BUILD_EVENT)
        self.pre_import_node: etree.ElementBase = self.ppj_root.find(XmlTagName.PRE_IMPORT_EVENT)
        self.post_import_node: etree.ElementBase = self.ppj_root.find(XmlTagName.POST_IMPORT_EVENT)
        self.pre_compile_node: etree.ElementBase = self.ppj_root.find(XmlTagName.PRE_COMPILE_EVENT)
        self.post_compile_node: etree.ElementBase = self.ppj_root.find(XmlTagName.POST_COMPILE_EVENT)
        self.pre_anonymize_node: etree.ElementBase = self.ppj_root.find(XmlTagName.PRE_ANONYMIZE_EVENT)
        self.post_anonymize_node: etree.ElementBase = self.ppj_root.find(XmlTagName.POST_ANONYMIZE_EVENT)
        self.pre_package_node: etree.ElementBase = self.ppj_root.find(XmlTagName.PRE_PACKAGE_EVENT)
        self.post_package_node: etree.ElementBase = self.ppj_root.find(XmlTagName.POST_PACKAGE_EVENT)
        self.pre_zip_node: etree.ElementBase = self.ppj_root.find(XmlTagName.PRE_ZIP_EVENT)
        self.post_zip_node: etree.ElementBase = self.ppj_root.find(XmlTagName.POST_ZIP_EVENT)

        self.optimize: bool = self.get_boolean_attribute(self.ppj_root, XmlAttributeName.OPTIMIZE)
        self.release: bool = self.get_boolean_attribute(self.ppj_root, XmlAttributeName.RELEASE)
        self.final: bool = self.get_boolean_attribute(self.ppj_root, XmlAttributeName.FINAL)
        self.anonymize: bool = self.get_boolean_attribute(self.ppj_root, XmlAttributeName.ANONYMIZE)
        self.package: bool = self.get_boolean_attribute(self.ppj_root, XmlAttributeName.PACKAGE)
        self.zip: bool = self.get_boolean_attribute(self.ppj_root, XmlAttributeName.ZIP)

        self.use_pre_build_event: bool = self.get_boolean_attribute(self.pre_build_node, XmlAttributeName.USE_IN_BUILD)
        self.use_post_build_event: bool = self.get_boolean_attribute(self.post_build_node, XmlAttributeName.USE_IN_BUILD)
        self.use_pre_import_event: bool = self.get_boolean_attribute(self.pre_import_node, XmlAttributeName.USE_IN_BUILD)
        self.use_post_import_event: bool = self.get_boolean_attribute(self.post_import_node, XmlAttributeName.USE_IN_BUILD)
        self.use_pre_compile_event: bool = self.get_boolean_attribute(self.pre_compile_node, XmlAttributeName.USE_IN_BUILD)
        self.use_post_compile_event: bool = self.get_boolean_attribute(self.post_compile_node, XmlAttributeName.USE_IN_BUILD)
        self.use_pre_anonymize_event: bool = self.get_boolean_attribute(self.pre_anonymize_node, XmlAttributeName.USE_IN_BUILD)
        self.use_post_anonymize_event: bool = self.get_boolean_attribute(self.post_anonymize_node, XmlAttributeName.USE_IN_BUILD)
        self.use_pre_package_event: bool = self.get_boolean_attribute(self.pre_package_node, XmlAttributeName.USE_IN_BUILD)
        self.use_post_package_event: bool = self.get_boolean_attribute(self.post_package_node, XmlAttributeName.USE_IN_BUILD)
        self.use_pre_zip_event: bool = self.get_boolean_attribute(self.pre_zip_node, XmlAttributeName.USE_IN_BUILD)
        self.use_post_zip_event: bool = self.get_boolean_attribute(self.post_zip_node, XmlAttributeName.USE_IN_BUILD)

    @property
    def game_type(self) -> str:
        return self.ppj_root.get(XmlAttributeName.GAME, default='')

    @property
    def flags_path(self) -> str:
        return self.ppj_root.get(XmlAttributeName.FLAGS, default='')

    @property
    def output_path(self) -> str:
        return self.ppj_root.get(XmlAttributeName.OUTPUT, default='')

    @property
    def packages_output(self) -> str:
        return self.packages_node.get(XmlAttributeName.OUTPUT, default='') if self.packages_node is not None else ''

    @property
    def zip_output(self) -> str:
        return self.zip_files_node.get(XmlAttributeName.OUTPUT, default='') if self.zip_files_node is not None else ''

    def update_attributes(self, parse_func) -> None:
        """Updates attributes of element tree with missing attributes and default values"""
        ppj_bool_keys = [
            XmlAttributeName.OPTIMIZE,
            XmlAttributeName.RELEASE,
            XmlAttributeName.FINAL,
            XmlAttributeName.ANONYMIZE,
            XmlAttributeName.PACKAGE,
            XmlAttributeName.ZIP
        ]

        other_bool_keys = [
            XmlAttributeName.NO_RECURSE,
            XmlAttributeName.USE_IN_BUILD
        ]

        parent_node = self.ppj_root.node
        for node in parent_node.getiterator():
            if node.text:
                node.text = parse_func(node.text.strip())

            tag = node.tag.replace('{%s}' % self.ppj_root.ns, '')

            if tag == XmlTagName.PAPYRUS_PROJECT:
                if XmlAttributeName.GAME not in node.attrib:
                    node.set(XmlAttributeName.GAME, '')
                if XmlAttributeName.FLAGS not in node.attrib:
                    node.set(XmlAttributeName.FLAGS, '')
                if XmlAttributeName.OUTPUT not in node.attrib:
                    node.set(XmlAttributeName.OUTPUT, '')
                for key in ppj_bool_keys:
                    if key not in node.attrib:
                        node.set(key, 'False')

            elif tag == XmlTagName.PACKAGES:
                if XmlAttributeName.OUTPUT not in node.attrib:
                    node.set(XmlAttributeName.OUTPUT, '')

            elif tag == XmlTagName.PACKAGE:
                if XmlAttributeName.NAME not in node.attrib:
                    node.set(XmlAttributeName.NAME, '')
                if XmlAttributeName.ROOT_DIR not in node.attrib:
                    node.set(XmlAttributeName.ROOT_DIR, '')

            elif tag in (XmlTagName.FOLDER, XmlTagName.INCLUDE, XmlTagName.MATCH):
                if XmlAttributeName.NO_RECURSE not in node.attrib:
                    node.set(XmlAttributeName.NO_RECURSE, 'False')
                if tag in (XmlTagName.INCLUDE, XmlTagName.MATCH):
                    if XmlAttributeName.PATH not in node.attrib:
                        node.set(XmlAttributeName.PATH, '')
                if tag == XmlTagName.MATCH:
                    if XmlAttributeName.IN not in node.attrib:
                        node.set(XmlAttributeName.IN, os.curdir)
                    if XmlAttributeName.EXCLUDE not in node.attrib:
                        node.set(XmlAttributeName.EXCLUDE, '')

            elif tag == XmlTagName.ZIP_FILES:
                if XmlAttributeName.OUTPUT not in node.attrib:
                    node.set(XmlAttributeName.OUTPUT, '')

            elif tag == XmlTagName.ZIP_FILE:
                if XmlAttributeName.NAME not in node.attrib:
                    node.set(XmlAttributeName.NAME, '')
                if XmlAttributeName.ROOT_DIR not in node.attrib:
                    node.set(XmlAttributeName.ROOT_DIR, '')
                if XmlAttributeName.COMPRESSION not in node.attrib:
                    node.set(XmlAttributeName.COMPRESSION, 'deflate')
                else:
                    node.set(XmlAttributeName.COMPRESSION, node.get(XmlAttributeName.COMPRESSION).casefold())

            elif tag in (XmlTagName.PRE_BUILD_EVENT, XmlTagName.POST_BUILD_EVENT,
                         XmlTagName.PRE_IMPORT_EVENT, XmlTagName.POST_IMPORT_EVENT):
                if XmlAttributeName.DESCRIPTION not in node.attrib:
                    node.set(XmlAttributeName.DESCRIPTION, '')
                if XmlAttributeName.USE_IN_BUILD not in node.attrib:
                    node.set(XmlAttributeName.USE_IN_BUILD, 'True')

            # parse values
            for key, value in node.attrib.items():
                value = value.casefold() in ('true', '1') if key in ppj_bool_keys + other_bool_keys else parse_func(value)
                node.set(key, str(value))

    def get_boolean_attribute(self, element: Union[etree._Element, XmlRoot], attr_name: str, default: bool = False) -> bool:
        if element is None:
            return default
        return element.get(attr_name) == 'True'
