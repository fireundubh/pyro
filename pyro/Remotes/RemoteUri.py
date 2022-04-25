from dataclasses import dataclass, field


@dataclass
class RemoteUri:
    owner: str = field(init=False, default_factory=str)
    repo: str = field(init=False, default_factory=str)
    branch: str = field(init=False, default_factory=str)
    data: dict = field(init=False, default=dict)  # type: ignore
    url: str = field(init=False, default_factory=str)
