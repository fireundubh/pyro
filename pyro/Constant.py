from dataclasses import dataclass


@dataclass
class Constant:
    @classmethod
    def items(cls) -> list[tuple[str, str]]:
        return list((k, getattr(cls, k)) for k in cls.__annotations__)

    @classmethod
    def keys(cls) -> list[str]:
        return list(k for k in cls.__annotations__)

    @classmethod
    def values(cls) -> list[str]:
        return list(getattr(cls, k) for k in cls.__annotations__)

    @classmethod
    def get(cls, field_name: str) -> str:
        uc_field_name: str = field_name.upper()
        return getattr(cls, uc_field_name) if uc_field_name in cls.keys() else ''
