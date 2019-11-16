from pyro.ProjectOptions import ProjectOptions


class PexReader:
    def __init__(self, options: ProjectOptions) -> None:
        self.options = options

    def get_compilation_time(self, path: str) -> int:
        with open(path, 'rb') as f:
            if self.options.game_type == 'fo4':
                f.seek(8)
                time_t_raw = f.read(8)
                time_t = int.from_bytes(time_t_raw, 'little', signed=False)
            else:
                f.seek(9)
                time_t_raw = f.read(4)
                time_t = int.from_bytes(time_t_raw, 'little', signed=False)

        return time_t
