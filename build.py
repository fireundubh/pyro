import argparse
import glob
import logging
import os
import shutil
import subprocess
import sys
import zipfile

from pyro.Comparators import endswith


class Application:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname).4s] %(message)s')
    log: logging.Logger = logging.getLogger('pyro')

    def __init__(self, args: argparse.Namespace) -> None:
        self.root_path: str = os.path.dirname(__file__)

        self.local_venv_path: str = args.local_venv_path
        self.package_name: str = 'pyro'
        self.no_zip: bool = args.no_zip
        self.vcvars64_path: str = args.vcvars64_path

        self.dist_path: str = os.path.join(self.root_path, f'{self.package_name}.dist')
        self.root_tools_path: str = os.path.join(self.root_path, 'tools')
        self.dist_tools_path: str = os.path.join(self.dist_path, 'tools')

        self.site_path: str = os.path.join(self.dist_path, 'site')
        self.zip_path: str = os.path.join(self.root_path, 'bin', f'{self.package_name}.zip')

        self.dist_glob_pattern: str = os.path.join(self.dist_path, r'**\*')

        self.icon_path: str = os.path.join(self.root_path, 'fire.ico')

        pyro_version: str = '1.0.0.0'

        self.nuitka_args: list = [
            'python', '-m', 'nuitka',
            '--standalone', 'pyro',
            '--include-package=pyro',
            '--assume-yes-for-downloads',
            '--plugin-enable=multiprocessing',
            '--plugin-enable=pkg-resources',
            '--msvc=14.3',
            '--disable-ccache',
            '--windows-company-name=fireundubh',
            f'--windows-product-name={self.package_name.capitalize()}',
            f'--windows-file-version={pyro_version}',
            f'--windows-product-version={pyro_version}',
            '--windows-file-description=https://github.com/fireundubh/pyro',
            '--windows-icon-from-ico=fire.ico'
        ]

    def __setattr__(self, key: str, value: object) -> None:
        # sanitize paths
        if isinstance(value, str) and endswith(key, 'path', ignorecase=True):
            value = os.path.normpath(value)
            # normpath converts empty paths to os.curdir which we don't want
            if value == os.curdir:
                value = ''
        super(Application, self).__setattr__(key, value)

    def _clean_dist_folder(self) -> None:
        if not os.path.exists(self.dist_path):
            return

        files_to_keep: tuple = (
            f'{self.package_name}.exe',
            'libcrypto-1_1.dll',
            'libssl-1_1.dll',
            'python37.dll',
            'python38.dll',
            'python39.dll',
            'python310.dll',
            '_elementpath.pyd',
            '_hashlib.pyd',
            '_multiprocessing.pyd',
            '_psutil_windows.pyd',
            '_queue.pyd',
            '_socket.pyd',
            '_ssl.pyd',
            'etree.pyd',
            'select.pyd',
            'unicodedata.pyd'
        )

        for f in glob.iglob(self.dist_glob_pattern, recursive=True):
            if not os.path.isfile(f):
                continue

            _, file_name = os.path.split(f)
            if file_name.casefold() in files_to_keep:
                continue

            Application.log.warning(f'Deleting: "{f}"')
            os.remove(f)

        for f in glob.iglob(self.dist_glob_pattern, recursive=True):
            if not os.path.isdir(f):
                continue

            if not os.listdir(f):
                Application.log.warning(f'Deleting empty folder: "{f}"')
                shutil.rmtree(f, ignore_errors=True)

        if os.path.exists(self.site_path):
            shutil.rmtree(self.site_path, ignore_errors=True)

    def _build_zip_archive(self) -> None:
        os.makedirs(os.path.dirname(self.zip_path), exist_ok=True)

        files: list = [f for f in glob.glob(self.dist_glob_pattern, recursive=True)
                       if os.path.isfile(f)]

        with zipfile.ZipFile(self.zip_path, 'w') as z:
            for f in files:
                z.write(f, os.path.join(self.package_name, os.path.relpath(f, self.dist_path)),
                        compress_type=zipfile.ZIP_STORED)
                Application.log.info(f'Added file to archive: {f}')

    @staticmethod
    def exec_process(cmd: list, env: dict) -> int:
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, universal_newlines=True, env=env)
            while process.poll() is None:
                line: str = process.stdout.readline().strip()
                if line:
                    Application.log.info(line)
        except FileNotFoundError:
            Application.log.error(f'Cannot run command: {cmd}')
            return 1
        return 0

    def run(self) -> int:
        if not sys.platform == 'win32':
            Application.log.error('Cannot build Pyro with Nuitka on a non-Windows platform')
            sys.exit(1)

        if self.vcvars64_path:
            if not os.path.exists(self.vcvars64_path) or not endswith(self.vcvars64_path, '.bat', ignorecase=True):
                Application.log.error('Cannot build Pyro with MSVC compiler because VsDevCmd path is invalid')
                sys.exit(1)

        Application.log.info(f'Using project path: "{self.root_path}"')

        Application.log.warning(f'Cleaning: "{self.dist_path}"')
        shutil.rmtree(self.dist_path, ignore_errors=True)
        os.makedirs(self.dist_path, exist_ok=True)

        fail_state: int = 0

        env_log_path: str = ''
        environ: dict = os.environ.copy()

        if self.vcvars64_path:
            try:
                process = subprocess.Popen(f'%comspec% /C "{self.vcvars64_path}"', stdout=subprocess.PIPE, shell=True, universal_newlines=True)
            except FileNotFoundError:
                fail_state = 1

            # noinspection PyUnboundLocalVariable
            while process.poll() is None:
                line = process.stdout.readline().strip()
                Application.log.info(line)

                if 'post-execution' in line:
                    _, env_log_path = line.split(' to ')
                    process.terminate()

            Application.log.info(f'Loading environment: "{env_log_path}"')

            with open(env_log_path, encoding='utf-8') as f:
                lines: list = f.read().splitlines()

                for line in lines:
                    key, value = line.split('=', maxsplit=1)
                    environ[key] = value

        if fail_state == 0:
            fail_state = self.exec_process(self.local_venv_path.split(' '), environ)

        if fail_state == 0:
            fail_state = self.exec_process(self.nuitka_args, environ)

        if fail_state == 0 and not os.path.exists(self.dist_path) or f'{self.package_name}.exe' not in os.listdir(self.dist_path):
            Application.log.error(f'Cannot find {self.package_name}.exe in folder or folder does not exist: {self.dist_path}')
            fail_state = 1

        if fail_state == 0:
            Application.log.info('Removing unnecessary files...')
            self._clean_dist_folder()

            Application.log.info('Copying schemas...')
            for schema_file_name in ['PapyrusProject.xsd']:
                shutil.copy2(os.path.join(self.root_path, self.package_name, schema_file_name),
                             os.path.join(self.dist_path, schema_file_name))

            Application.log.info('Copying tools...')
            os.makedirs(self.dist_tools_path, exist_ok=True)

            for tool_file_name in ['bsarch.exe', 'bsarch.license.txt']:
                shutil.copy2(os.path.join(self.root_tools_path, tool_file_name),
                             os.path.join(self.dist_tools_path, tool_file_name))

            if not self.no_zip:
                Application.log.info('Building archive...')
                self._build_zip_archive()

                Application.log.info(f'Wrote archive: "{self.zip_path}"')

            Application.log.info('Build complete.')

            return fail_state

        Application.log.error(f'Failed to execute command: {" ".join(self.nuitka_args)}')

        Application.log.warning(f'Resetting: "{self.dist_path}"')
        shutil.rmtree(self.dist_path, ignore_errors=True)

        return fail_state


if __name__ == '__main__':
    _parser = argparse.ArgumentParser(description='Pyro Build Script')

    _parser.add_argument('--local-venv-path',
                         action='store', default=os.path.join(os.path.dirname(sys.executable), 'activate.bat'),
                         help='path to local venv activate script')

    _parser.add_argument('--no-zip',
                         action='store_true', default=False,
                         help='do not create zip archive')

    _parser.add_argument('--vcvars64-path',
                         action='store', default='',
                         help='path to visual studio developer command prompt')

    Application(_parser.parse_args()).run()
