import re
import subprocess

from pyro.Logger import Logger


class ProcessManager:
    log = Logger()

    @staticmethod
    def run(command: str, use_bsarch: bool = False) -> int:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, universal_newlines=True)

        exclusions = ('Starting', 'Assembly', 'Compilation', 'Batch', 'Copyright', 'Papyrus', 'Failed', 'No output')

        line_error = re.compile('\(\d+,\d+\)')

        try:
            while process.poll() is None:
                line = process.stdout.readline().strip()

                if use_bsarch:
                    ProcessManager.log.bsarch(line) if line else None
                else:
                    exclude_lines = not line.startswith(exclusions)
                    ProcessManager.log.compiler(line) if line and exclude_lines and 'error(s)' not in line else None

                    if line_error.match(line) is not None:
                        process.terminate()
                        return -1

        except KeyboardInterrupt:
            try:
                process.terminate()
            except OSError:
                ProcessManager.log.error('Process interrupted by user.')
            return -1

        return 0
