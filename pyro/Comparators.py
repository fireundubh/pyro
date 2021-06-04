import os
from typing import Union

from lxml import etree


def startswith(a_source: str, a_prefix: Union[str, tuple],
               a_start: int = None, a_end: int = None, /, ignorecase: bool = False) -> bool:

    source = a_source[a_start:a_end]

    prefixes = a_prefix if isinstance(a_prefix, tuple) else (a_prefix,)

    for prefix in prefixes:
        source_prefix = source[:len(prefix)]

        if not ignorecase:
            if source_prefix == prefix:
                return True
        else:
            if source_prefix.casefold() == prefix.casefold():
                return True

    return False


def endswith(a_source: str, a_suffix: Union[str, tuple],
             a_start: int = None, a_end: int = None, /, ignorecase: bool = False) -> bool:

    source = a_source[a_start:a_end]

    suffixes = a_suffix if isinstance(a_suffix, tuple) else (a_suffix,)

    for suffix in suffixes:
        source_suffix = source[-len(suffix):]

        if not ignorecase:
            if source_suffix == suffix:
                return True
        else:
            if source_suffix.casefold() == suffix.casefold():
                return True

    return False


def is_command_node(node: etree.ElementBase) -> bool:
    return node is not None and endswith(node.tag, 'Command') and node.text is not None


def is_folder_node(node: etree.ElementBase) -> bool:
    return node is not None and endswith(node.tag, 'Folder') and node.text is not None


def is_import_node(node: etree.ElementBase) -> bool:
    return node is not None and endswith(node.tag, 'Import') and node.text is not None


def is_include_node(node: etree.ElementBase) -> bool:
    return node is not None and endswith(node.tag, 'Include') and node.text is not None


def is_package_node(node: etree.ElementBase) -> bool:
    return node is not None and endswith(node.tag, 'Package')


def is_script_node(node: etree.ElementBase) -> bool:
    return node is not None and endswith(node.tag, 'Script') and node.text is not None


def is_variable_node(node: etree.ElementBase) -> bool:
    return node is not None and endswith(node.tag, 'Variable')


def is_zipfile_node(node: etree.ElementBase) -> bool:
    return node is not None and endswith(node.tag, 'ZipFile')


def is_namespace_path(node: etree.ElementBase) -> bool:
    return not os.path.isabs(node.text) and ':' in node.text
