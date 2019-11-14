import os

from argparse import Namespace
from dataclasses import dataclass, field


@dataclass
class ProjectOptions:
    args: Namespace = field(repr=False, default_factory=Namespace)

    # required arguments
    input_path: str = field(init=False, default_factory=lambda: '')

    # optional arguments
    game_type: str = field(init=False, default_factory=lambda: '')
    disable_anonymizer: bool = field(init=False, default_factory=bool)
    disable_bsarch: bool = field(init=False, default_factory=bool)
    disable_parallel: bool = field(init=False, default_factory=bool)

    # pyro paths
    temp_path: str = field(init=False, default_factory=lambda: r'..\temp')
    bsarch_path: str = field(init=False, default_factory=lambda: r'..\tools\bsarch.exe')

    # shared paths
    game_path: str = field(init=False, default_factory=lambda: '')
    source_path: str = field(init=False, default_factory=lambda: r'Data\Scripts\Source')
    base_path: str = field(init=False, default_factory=lambda: r'Data\Scripts\Source\Base')
    user_path: str = field(init=False, default_factory=lambda: r'Data\Scripts\Source\User')

    # compiler paths
    compiler_path: str = field(init=False, default_factory=lambda: r'Papyrus Compiler\PapyrusCompiler.exe')

    # flags paths
    fo4_flags_path: str = field(init=False, default_factory=lambda: '')
    tesv_flags_path: str = field(init=False, default_factory=lambda: '')
    sse_flags_path: str = field(init=False, default_factory=lambda: '')

    # registry paths
    fo4_registry_path: str = field(init=False, default_factory=lambda: r'SOFTWARE\WOW6432Node\Bethesda Softworks\Fallout4\Installed Path')
    tesv_registry_path: str = field(init=False, default_factory=lambda: r'SOFTWARE\WOW6432Node\Bethesda Softworks\Skyrim\Installed Path')
    sse_registry_path: str = field(init=False, default_factory=lambda: r'SOFTWARE\WOW6432Node\Bethesda Softworks\Skyrim Special Edition\Installed Path')

    def __post_init__(self) -> None:
        self.fo4_flags_path = os.path.join(self.base_path, 'Institute_Papyrus_Flags.flg')
        self.tesv_flags_path = os.path.join(self.source_path, 'TESV_Papyrus_Flags.flg')
        self.sse_flags_path = os.path.join(self.base_path, 'TESV_Papyrus_Flags.flg')

        for key in self.__dict__:
            if key == 'args':
                continue
            try:
                user_value = getattr(self.args, key)
                if user_value != getattr(self, key):
                    setattr(self, key, user_value)
            except AttributeError:
                continue
