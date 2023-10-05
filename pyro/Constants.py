from pyro.Constant import Constant


class FlagsName(Constant):
    FO4: str = 'Institute_Papyrus_Flags.flg'
    SF1: str = 'Starfield_Papyrus_Flags.flg'
    SSE: str = 'TESV_Papyrus_Flags.flg'
    TES5: str = 'TESV_Papyrus_Flags.flg'


class GameName(Constant):
    FO4: str = 'Fallout 4'
    SF1: str = 'Starfield'
    SSE: str = 'Skyrim Special Edition'
    TES5: str = 'Skyrim'


class GameType(Constant):
    FO4: str = 'fo4'
    SF1: str = 'sf1'
    SSE: str = 'sse'
    TES5: str = 'tes5'


class XmlAttributeName(Constant):
    ANONYMIZE: str = 'Anonymize'
    COMPRESSION: str = 'Compression'
    DESCRIPTION: str = 'Description'
    EXCLUDE: str = 'Exclude'
    FINAL: str = 'Final'
    FLAGS: str = 'Flags'
    GAME: str = 'Game'
    IN: str = 'In'
    NAME: str = 'Name'
    NO_RECURSE: str = 'NoRecurse'
    OPTIMIZE: str = 'Optimize'
    OUTPUT: str = 'Output'
    PACKAGE: str = 'Package'
    PATH: str = 'Path'
    RELEASE: str = 'Release'
    ROOT_DIR: str = 'RootDir'
    USE_IN_BUILD: str = 'UseInBuild'
    VALUE: str = 'Value'
    ZIP: str = 'Zip'


class XmlTagName(Constant):
    FOLDER: str = 'Folder'
    FOLDERS: str = 'Folders'
    IMPORT: str = 'Import'
    IMPORTS: str = 'Imports'
    INCLUDE: str = 'Include'
    MATCH: str = 'Match'
    PACKAGE: str = 'Package'
    PACKAGES: str = 'Packages'
    PAPYRUS_PROJECT: str = 'PapyrusProject'
    POST_BUILD_EVENT: str = 'PostBuildEvent'
    POST_IMPORT_EVENT: str = 'PostImportEvent'
    POST_COMPILE_EVENT: str = 'PostCompileEvent'
    POST_ANONYMIZE_EVENT: str = 'PostAnonymizeEvent'
    POST_PACKAGE_EVENT: str = 'PostPackageEvent'
    POST_ZIP_EVENT: str = 'PostZipEvent'
    PRE_BUILD_EVENT: str = 'PreBuildEvent'
    PRE_IMPORT_EVENT: str = 'PreImportEvent'
    PRE_COMPILE_EVENT: str = 'PreCompileEvent'
    PRE_ANONYMIZE_EVENT: str = 'PreAnonymizeEvent'
    PRE_PACKAGE_EVENT: str = 'PrePackageEvent'
    PRE_ZIP_EVENT: str = 'PreZipEvent'
    SCRIPTS: str = 'Scripts'
    VARIABLES: str = 'Variables'
    ZIP_FILE: str = 'ZipFile'
    ZIP_FILES: str = 'ZipFiles'


__all__ = ['FlagsName', 'GameName', 'GameType', 'XmlAttributeName', 'XmlTagName']
