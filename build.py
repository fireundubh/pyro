import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from glob import glob

version = '1.3.4'


class Application:
    def __init__(self, args: argparse.Namespace) -> None:
        self.cwd: str = os.getcwd()

        self.package_name = args.package_name

        self.dist_folder = os.path.normpath(os.path.join(self.cwd, '%s.dist' % self.package_name))
        self.tools_dir_src = os.path.normpath(os.path.join(os.path.dirname(__file__), 'tools'))
        self.tools_dir_dst = os.path.normpath(os.path.join(self.dist_folder, 'tools'))

    def _clean_dist_folder(self) -> None:
        if not os.path.exists(self.dist_folder):
            return

        files_to_keep = (
            '%s.exe' % self.package_name,
            'python37.dll',
            '_multiprocessing.pyd',
            '_queue.pyd',
            '_socket.pyd',
            'select.pyd',
            '_elementpath.pyd',
            'etree.pyd'
        )

        files = [f for f in glob(os.path.join(self.dist_folder, '**\*'), recursive=True)
                 if os.path.isfile(f) and not f.endswith(files_to_keep)]

        for f in files:
            os.remove(f)
            print('Deleted: %s' % f)

        site_dir = os.path.join(self.dist_folder, 'site')
        if os.path.exists(site_dir):
            shutil.rmtree(site_dir, ignore_errors=True)

    def _build_zip_archive(self) -> str:
        zip_file: str = '%s_v%s.zip' % (self.package_name, version.replace('.', '-'))
        zip_path: str = os.path.join(self.cwd, 'bin', zip_file)
        os.makedirs(os.path.dirname(zip_path), exist_ok=True)

        files = [f for f in glob(os.path.join(self.dist_folder, '**\*'), recursive=True) if os.path.isfile(f)]

        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_LZMA) as z:
            for f in files:
                z.write(f, os.path.join(self.package_name, os.path.relpath(f, self.dist_folder)), compress_type=zipfile.ZIP_LZMA)
                print('Added file to archive: %s' % f)

        return zip_path

    def run(self) -> int:
        if os.path.exists(self.dist_folder):
            shutil.rmtree(self.dist_folder, ignore_errors=True)

        # noinspection PyListCreation
        args: list = [
            'pipenv',
            'run',
            'nuitka',
            '--standalone', 'pyro',
            '--include-package=pyro',
            '--experimental=use_pefile',
            '--python-flag=no_site',
            '--python-flag=nosite',
            '--python-for-scons=%s' % sys.executable,
            '--assume-yes-for-downloads',
            '--plugin-enable=multiprocessing',
            '--show-progress',
            '--file-reference-choice=runtime'
        ]

        retcode: int = subprocess.call(args)
        if retcode != 0:
            return retcode

        print('Cleaning up dist folder...')
        self._clean_dist_folder()

        os.makedirs(self.tools_dir_dst, exist_ok=True)
        for f in ('bsarch.exe', 'bsarch.license.txt'):
            shutil.copy2(os.path.join(self.tools_dir_src, f), os.path.join(self.tools_dir_dst, f))

        # shutil.copy2(os.path.join(self.tools_dir_src, 'test.bat'), os.path.join(self.dist_folder, 'test.bat'))

        print('Building archive...')
        zip_created: str = self._build_zip_archive()
        print('Wrote archive: %s' % zip_created)

        return 0


if __name__ == '__main__':
    _parser = argparse.ArgumentParser()
    _parser.add_argument('-p', '--package-name', action='store', type=str, default='pyro')
    Application(_parser.parse_args()).run()
