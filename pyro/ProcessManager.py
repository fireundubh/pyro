import re
import subprocess

from pyro.Logger import Logger


class ProcessManager:
    log = Logger()

    @staticmethod
    def run(command: str, use_bsarch: bool = False) -> int:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, universal_newlines=True)

        papyrus_exclusions = ('Starting', 'Assembly', 'Compilation', 'Batch', 'Copyright', 'Papyrus', 'Failed', 'No output')
        bsarch_exclusions = ('BSArch', 'Packer', 'Version', 'Files', 'Archive Flags', '[', '*', 'Compressed', 'Retain', 'XBox', 'Startup', 'Embed', 'XMem', 'Bit', 'Format')

        line_error = re.compile('\(\d+,\d+\)')

        try:
            while process.poll() is None:
                line = process.stdout.readline().strip()

                if use_bsarch:
                    if line.startswith(bsarch_exclusions):
                        continue

                    if line.startswith('Packing'):
                        package_path = line.split(':', 1)[1].strip()
                        ProcessManager.log.bsarch('Packing folder "%s"...' % package_path)
                        continue

                    if line.startswith('Archive Name'):
                        archive_path = line.split(':', 1)[1].strip()
                        ProcessManager.log.bsarch('Building "%s"...' % archive_path)
                        continue

                    if line.startswith('Done'):
                        archive_time = line.split('in')[1].strip()[:-1]
                        hours, minutes, seconds = [round(float(n), 2) for n in archive_time.split(':')]

                        timecode = ''
                        if hours > 0.0 and minutes > 0.0 and seconds > 0.0:
                            timecode = '%sh %sm %ss' % (hours, minutes, seconds)
                        elif hours == 0.0 and minutes > 0.0 and seconds > 0.0:
                            timecode = '%sm %ss' % (minutes, seconds)
                        elif hours == 0.0 and minutes == 0.0 and seconds > 0.0:
                            timecode = '%ss' % seconds

                        ProcessManager.log.pyro('Packaging time: %s' % timecode)
                        continue

                    ProcessManager.log.bsarch(line) if line else None
                else:
                    exclude_lines = not line.startswith(papyrus_exclusions)
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
