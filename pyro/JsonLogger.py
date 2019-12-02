import json
import os

from pyro.PapyrusProject import PapyrusProject


class JsonLogger:
    def __init__(self, ppj: PapyrusProject):
        self.ppj = ppj

        files = os.listdir(self.ppj.options.log_path) if self.ppj.options.log_path else []
        self.log_file = files[-1:][0] if files else ''

    def add_record(self, key: str, value: object) -> None:
        if not self.ppj.options.log_path or not self.log_file:
            return

        path = os.path.join(self.ppj.options.log_path, self.log_file)

        with open(path, encoding='utf-8') as r:
            data = json.load(r)

        data[key] = value

        with open(path, mode='w', encoding='utf-8') as w:
            json.dump(data, w, indent=2)
