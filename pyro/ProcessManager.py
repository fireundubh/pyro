import re
import subprocess
from decimal import Decimal

from pyro.Logger import Logger


class ProcessManager(Logger):
    @staticmethod
    def run(command: str, use_bsarch: bool = False) -> int:
        if len(command) > 32768:
            ProcessManager.log.error('Cannot create process because command exceeds max length: %s' % len(command))
            return 1

        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        except WindowsError as e:
            ProcessManager.log.error('Cannot create process because: %s.' % e.strerror)
            return 1

        papyrus_exclusions = ('Starting', 'Assembly', 'Compilation', 'Batch', 'Copyright', 'Papyrus', 'Failed', 'No output')
        bsarch_exclusions = ('BSArch', 'Packer', 'Version', 'Files', 'Archive Flags', '[', '*', 'Compressed', 'Retain', 'XBox', 'Startup', 'Embed', 'XMem', 'Bit', 'Format')

        line_error = re.compile(r'\(\d+,\d+\)')

        try:
            while process.poll() is None:
                line = process.stdout.readline().strip()

                if use_bsarch:
                    if line.startswith(bsarch_exclusions):
                        continue

                    if line.startswith('Packing'):
                        package_path = line.split(':', 1)[1].strip()
                        ProcessManager.log.info('Packaging folder "%s"...' % package_path)
                        continue

                    if line.startswith('Archive Name'):
                        archive_path = line.split(':', 1)[1].strip()
                        ProcessManager.log.info('Building "%s"...' % archive_path)
                        continue

                    if line.startswith('Done'):
                        archive_time = line.split('in')[1].strip()[:-1]
                        hours, minutes, seconds = [round(Decimal(n), 3) for n in archive_time.split(':')]

                        timecode = ProcessManager._format_time(hours, minutes, seconds)

                        ProcessManager.log.info('Packaging time: %s' % timecode)
                        continue

                    if line:
                        ProcessManager.log.info(line)
                else:
                    exclude_lines = not line.startswith(papyrus_exclusions)

                    if line and exclude_lines and 'error(s)' not in line:
                        ProcessManager.log.info(line)

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

    @staticmethod
    def _format_time(hours: Decimal, minutes: Decimal, seconds: Decimal) -> str:
        if hours.compare(0) == 1 and minutes.compare(0) == 1 and seconds.compare(0) == 1:
            return '%sh %sm %ss' % (hours, minutes, seconds)
        if hours.compare(0) == 0 and minutes.compare(0) == 1 and seconds.compare(0) == 1:
            return '%sm %ss' % (minutes, seconds)
        if hours.compare(0) == 0 and minutes.compare(0) == 0 and seconds.compare(0) == 1:
            return '%ss' % seconds
        return '%sh %sm %ss' % (hours, minutes, seconds)
