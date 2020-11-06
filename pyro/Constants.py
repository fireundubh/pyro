from dataclasses import dataclass

from pyro.Constant import Constant


class FlagsName(Constant):
    FO4: str = 'Institute_Papyrus_Flags.flg'
    SSE: str = 'TESV_Papyrus_Flags.flg'
    TES5: str = 'TESV_Papyrus_Flags.flg'


class GameName(Constant):
    FO4: str = 'Fallout 4'
    SSE: str = 'Skyrim Special Edition'
    TES5: str = 'Skyrim'


class GameType(Constant):
    FO4: str = 'fo4'
    SSE: str = 'sse'
    TES5: str = 'tes5'


@dataclass
class XmlAttributeName:
    ANONYMIZE: str = 'Anonymize'
    COMPRESSION: str = 'Compression'
    DESCRIPTION: str = 'Description'
    FINAL: str = 'Final'
    FLAGS: str = 'Flags'
    GAME: str = 'Game'
    NAME: str = 'Name'
    NO_RECURSE: str = 'NoRecurse'
    OPTIMIZE: str = 'Optimize'
    OUTPUT: str = 'Output'
    PACKAGE: str = 'Package'
    RELEASE: str = 'Release'
    ROOT_DIR: str = 'RootDir'
    USE_IN_BUILD: str = 'UseInBuild'
    VALUE: str = 'Value'
    ZIP: str = 'Zip'


@dataclass
class XmlTagName:
    FOLDER: str = 'Folder'
    FOLDERS: str = 'Folders'
    IMPORT: str = 'Import'
    IMPORTS: str = 'Imports'
    INCLUDE: str = 'Include'
    PACKAGE: str = 'Package'
    PACKAGES: str = 'Packages'
    PAPYRUS_PROJECT: str = 'PapyrusProject'
    POST_BUILD_EVENT: str = 'PostBuildEvent'
    PRE_BUILD_EVENT: str = 'PreBuildEvent'
    SCRIPTS: str = 'Scripts'
    VARIABLES: str = 'Variables'
    ZIP_FILE: str = 'ZipFile'
    ZIP_FILES: str = 'ZipFiles'


__all__ = ['FlagsName', 'GameName', 'GameType', 'XmlAttributeName', 'XmlTagName']
