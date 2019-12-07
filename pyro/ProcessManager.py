import os
import re
import subprocess
from decimal import Decimal

from pyro.Logger import Logger
from pyro.ProcessState import ProcessState


class ProcessManager(Logger):
    @staticmethod
    def _format_time(hours: Decimal, minutes: Decimal, seconds: Decimal) -> str:
        if hours.compare(0) == 1 and minutes.compare(0) == 1 and seconds.compare(0) == 1:
            return '%sh %sm %ss' % (hours, minutes, seconds)
        if hours.compare(0) == 0 and minutes.compare(0) == 1 and seconds.compare(0) == 1:
            return '%sm %ss' % (minutes, seconds)
        if hours.compare(0) == 0 and minutes.compare(0) == 0 and seconds.compare(0) == 1:
            return '%ss' % seconds
        return '%sh %sm %ss' % (hours, minutes, seconds)

    @staticmethod
    def run_bsarch(command: str) -> ProcessState:
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        except WindowsError as e:
            ProcessManager.log.error('Cannot create process because: %s.' % e.strerror)
            return ProcessState.FAILURE

        exclusions = ('BSArch', 'Packer', 'Version', 'Files', 'Archive Flags', '[', '*', 'Compressed', 'Retain', 'XBox', 'Startup', 'Embed', 'XMem', 'Bit', 'Format')

        try:
            while process.poll() is None:
                line = process.stdout.readline().strip()

                if line.startswith(exclusions):
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

        except KeyboardInterrupt:
            try:
                process.terminate()
            except OSError:
                ProcessManager.log.error('Process interrupted by user.')
            return ProcessState.INTERRUPTED

        return ProcessState.SUCCESS

    @staticmethod
    def run_compiler(command: str) -> ProcessState:
        command_size = len(command)

        if command_size > 32768:
            ProcessManager.log.error('Cannot create process because command exceeds max length: %s' % command_size)
            return ProcessState.FAILURE

        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        except WindowsError as e:
            ProcessManager.log.error('Cannot create process because: %s.' % e.strerror)
            return ProcessState.FAILURE

        exclusions = ('Starting', 'Assembly', 'Compilation', 'Batch', 'Copyright', 'Papyrus', 'Failed', 'No output')

        line_error = re.compile(r'(.*)(\(\d+,\d+\)):\s+(.*)')

        try:
            while process.poll() is None:
                line = process.stdout.readline().strip()

                exclude_lines = not line.startswith(exclusions)

                match = line_error.search(line)

                if line and exclude_lines and match is None and 'error(s)' not in line:
                    ProcessManager.log.info(line)

                if match is not None:
                    path, location, message = match.groups()
                    head, tail = os.path.split(path)
                    ProcessManager.log.error(r'COMPILATION FAILED: %s\%s%s: %s' % (os.path.basename(head), tail, location, message))
                    process.terminate()
                    return ProcessState.ERRORS

        except KeyboardInterrupt:
            try:
                process.terminate()
            except OSError:
                ProcessManager.log.error('Process interrupted by user.')
            return ProcessState.INTERRUPTED

        return ProcessState.SUCCESS
