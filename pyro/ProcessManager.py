import logging
import os
import re
import subprocess
from decimal import Decimal

from lxml import etree

from pyro.Enums.ProcessState import ProcessState

from pyro.Comparators import (is_command_node,
                              startswith)
from pyro.Constants import XmlAttributeName


class ProcessManager:
    log: logging.Logger = logging.getLogger('pyro')

    @staticmethod
    def _format_time(hours: Decimal, minutes: Decimal, seconds: Decimal) -> str:
        if hours.compare(0) == 1 and minutes.compare(0) == 1 and seconds.compare(0) == 1:
            return f'{hours}h {minutes}m {seconds}s'
        if hours.compare(0) == 0 and minutes.compare(0) == 1 and seconds.compare(0) == 1:
            return f'{minutes}m {seconds}s'
        if hours.compare(0) == 0 and minutes.compare(0) == 0 and seconds.compare(0) == 1:
            return f'{seconds}s'
        return f'{hours}h {minutes}m {seconds}s'

    @staticmethod
    def run_event(event_node: etree.ElementBase, project_path: str) -> None:
        if event_node is None:
            return

        ProcessManager.log.info(event_node.get(XmlAttributeName.DESCRIPTION))

        ws: re.Pattern = re.compile('[ \t\n\r]+')

        environ: dict = os.environ.copy()
        # command: str = ' && '.join(
        #     ws.sub(' ', node.text)
        #     for node in filter(is_command_node, event_node)
        # )

        for node in filter(is_command_node, event_node):
            command = ws.sub(' ', node.text)
            ProcessManager.run_command(command, project_path, environ)

    @staticmethod
    def run_command(command: str, cwd: str, env: dict) -> ProcessState:
        try:
            process = subprocess.Popen(command,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT,
                                       universal_newlines=True,
                                       shell=True,
                                       cwd=cwd,
                                       env=env)
        except WindowsError as e:
            ProcessManager.log.error(f'Cannot create process because: {e.strerror}')
            return ProcessState.FAILURE

        try:
            while process.poll() is None:
                if (line := process.stdout.readline().strip()) != '':
                    ProcessManager.log.info(line)

        except KeyboardInterrupt:
            try:
                process.terminate()
            except OSError:
                ProcessManager.log.error('Process interrupted by user.')
            return ProcessState.INTERRUPTED

        return ProcessState.SUCCESS

    @staticmethod
    def run_bsarch(command: str) -> ProcessState:
        """
        Creates bsarch process and logs output to console

        :param command: Command to execute, including absolute path to executable and its arguments
        :return: ProcessState (SUCCESS, FAILURE, INTERRUPTED, ERRORS)
        """
        try:
            process = subprocess.Popen(command,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT,
                                       universal_newlines=True)
        except WindowsError as e:
            ProcessManager.log.error(f'Cannot create process because: {e.strerror}')
            return ProcessState.FAILURE

        exclusions = (
            '*',
            '[',
            'Archive Flags',
            'Bit',
            'BSArch',
            'Compressed',
            'Done',
            'Embed',
            'Files',
            'Format',
            'Packer',
            'Retain',
            'Startup',
            'Version',
            'XBox',
            'XMem'
        )

        try:
            while process.poll() is None:
                if (line := process.stdout.readline().strip()) != '':
                    if startswith(line, exclusions):
                        continue

                    if startswith(line, 'Packing'):
                        package_path = line.split(':', 1)[1].strip()
                        ProcessManager.log.info(f'Packaging folder "{package_path}"...')
                        continue

                    if startswith(line, 'Archive Name'):
                        archive_path = line.split(':', 1)[1].strip()
                        ProcessManager.log.info(f'Building "{archive_path}"...')
                        continue

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
        """
        Creates compiler process and logs output to console

        :param command: Command to execute, including absolute path to executable and its arguments
        :return: ProcessState (SUCCESS, FAILURE, INTERRUPTED, ERRORS)
        """
        command_size = len(command)
        
        using_caprica = command.lower().find("caprica.exe") != -1
        
        if command_size > 32766:
            ProcessManager.log.error(f'Cannot create process because command exceeds max length: {command_size}')
            return ProcessState.FAILURE

        try:
            process = subprocess.Popen(command,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT,
                                       universal_newlines=True)
        except WindowsError as e:
            ProcessManager.log.error(f'Cannot create process because: {e.strerror}')
            return ProcessState.FAILURE

        exclusions = (
            'Assembly',
            'Batch',
            'Compilation',
            'Copyright',
            'Failed',
            'No output',
            'Papyrus',
            'Starting'
        )

        # PapyrusCompiler's error structure:
        # filename      [example.psc]   (.*)
        # location      [(69,420)]      (\(-?\d*\.?\d+,-?\d*\.?\d+\))
        # error message [: bad molly]   :\s+(.*)
        line_error_papyrus = re.compile(r'(.*)(\(-?\d*\.?\d+,-?\d*\.?\d+\)):\s+(.*)')
        
        # Caprica's error structure:
        # filename      [example.psc ]  (.*)\s+
        # location      [(69, 4:20)]    (\(-?\d*\.?\d+, -?\d*\.?\d+:-?\d*\.?\d+\))
        # error/warning [: Warning 1: ] :\s+(.*):\s+
        # error message [bad molly]     (.*)
        line_error_caprica = re.compile(r'(.*)\s+(\(-?\d*\.?\d+, -?\d*\.?\d+:-?\d*\.?\d+\)):\s+(.*):\s+(.*)')
        
        line_error = line_error_caprica if using_caprica else line_error_papyrus

        error_count = 0

        try:
            while process.poll() is None:
                if (line := process.stdout.readline().strip()) != '':
                    if startswith(line, exclusions):
                        continue
                    
                    if (match := line_error.search(line)) is not None:
                        if (using_caprica):
                            path, location, message_type, message = match.groups()
                        else:
                            path, location, message = match.groups()
                        head, tail = os.path.split(path)
                        if not head:
                            script_path = tail
                        else:
                            script_path = f'{os.path.basename(head)}\\{tail}'

                        pyro_message = f'{script_path}{location}: {message}'
                        if (not using_caprica or message_type.lower() == "fatal error"):
                            ProcessManager.log.error(f'COMPILATION FAILED: {pyro_message}')
                            process.terminate()
                            error_count += 1
                        elif (message_type.lower() == "error"):
                            ProcessManager.log.error(f'COMPILATION ERROR: {pyro_message}')
                            error_count += 1
                        else:
                            ProcessManager.log.warning(f'{message_type}: {pyro_message}')

                    elif startswith(line, ('Error', 'Fatal Error'), ignorecase=True):
                        ProcessManager.log.error(line)
                        process.terminate()
                        error_count += 1

                    elif 'error(s)' not in line:
                        ProcessManager.log.info(line)

        except KeyboardInterrupt:
            try:
                process.terminate()
            except OSError:
                ProcessManager.log.error('Process interrupted by user.')
            return ProcessState.INTERRUPTED

        return ProcessState.SUCCESS if error_count == 0 else ProcessState.ERRORS
