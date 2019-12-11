from dataclasses import dataclass, field
from typing import IO

from pyro.PexTypes import PexInt
from pyro.PexTypes import PexStr


@dataclass
class PexHeader:
    size: int = field(init=False, default=0)
    endianness: str = field(init=False, default='little')

    magic: PexInt = field(init=False, default_factory=PexInt)
    major_version: PexInt = field(init=False, default_factory=PexInt)
    minor_version: PexInt = field(init=False, default_factory=PexInt)
    game_id: PexInt = field(init=False, default_factory=PexInt)
    compilation_time: PexInt = field(init=False, default_factory=PexInt)
    script_path_size: PexInt = field(init=False, default_factory=PexInt)
    script_path: PexStr = field(init=False, default_factory=PexStr)
    user_name_size: PexInt = field(init=False, default_factory=PexInt)
    user_name: PexStr = field(init=False, default_factory=PexStr)
    computer_name_size: PexInt = field(init=False, default_factory=PexInt)
    computer_name: PexStr = field(init=False, default_factory=PexStr)

    def read(self, f: IO, name: str, length: int) -> None:
        """Reads a set of bytes and their offset to an attribute by name"""
        if name not in self.__dict__:
            raise AttributeError('Attribute "%s" does not exist in PexHeader' % name)

        obj = getattr(self, name)
        obj.offset, obj.data = f.tell(), f.read(length)

        if isinstance(obj, PexInt):
            obj.value = int.from_bytes(obj.data, self.endianness, signed=False)
        elif isinstance(obj, PexStr):
            obj.value = obj.data.decode('ascii')
