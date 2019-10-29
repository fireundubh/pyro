import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from glob import glob

version='1.3.3'

class Application:
    def __init__(self, args: argparse.Namespace) -> None:
        self.cwd: str = os.getcwd()

        self.package_name = args.package_name

        if os.path.exists(args.python_path):
            self.python_path = args.python_path
        else:
            raise FileNotFoundError(args.python_path + ' does not exist')

    def _clean_dist_folder(self, path: str) -> None:
        files_to_keep: tuple = (
            '%s.exe' % self.package_name,
            'python37.dll',
            '_asyncio.pyd',
            '_ctypes.pyd',
            '_overlapped.pyd',
            '_socket.pyd',
            'select.pyd',
            'unicodedata.pyd',
            'etree.pyd',
            '_elementpath.pyd',
            '_queue.pyd',
            '_multiprocessing.pyd'
        )

        if not os.path.exists(path):
            return

        files: list = [f for f in glob(os.path.join(path, '**\*'), recursive=True)
                       if os.path.isfile(f) and not f.endswith(files_to_keep)]

        for f in files:
            os.remove(f)
            print('Deleted: %s' % f)

    def _build_zip_archive(self, path: str) -> str:
        zip_file: str = '%s_v%s.zip' % (self.package_name, version.replace('.', '-'))
        zip_path: str = os.path.join(self.cwd, 'bin', zip_file)
        os.makedirs(os.path.dirname(zip_path), exist_ok=True)

        files: list = [f for f in glob(os.path.join(path, '**\*'), recursive=True) if os.path.isfile(f)]

        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_LZMA) as z:
            for f in files:
                z.write(f, os.path.join(self.package_name, os.path.relpath(f, path)), compress_type=zipfile.ZIP_LZMA)
                print('Added file to archive: %s' % f)

        return zip_path

    def run(self) -> int:
        package_path: str = os.path.join(self.cwd, self.package_name)

        dist_folder: str = os.path.join(self.cwd, '%s.dist' % self.package_name)
        if os.path.exists(dist_folder):
            shutil.rmtree(dist_folder, ignore_errors=True)

        # noinspection PyListCreation
        args: list = [
            self.python_path,
            '-m', 'nuitka',
            '--standalone','pyro_cli',
            '--include-package=pyro',
            '--experimental=use_pefile',
            '--python-flag=no_site',
            '--python-flag=nosite',
            '--python-for-scons=%s' % sys.executable,
            '--assume-yes-for-downloads',
            '--plugin-enable=multiprocessing',
            '--show-progress'
        ]

#        args.append('--output-dir=%s' % self.cwd)
#        args.append('%s' % package_path)

        retcode: int = subprocess.call(args)
        if retcode != 0:
            return retcode

# It seems like we need just about everything
#        print('Cleaning up dist folder...')
#        self._clean_dist_folder(dist_folder)

        print('Building archive...')
        shutil.copyfile(os.path.join('pyro_cli','pyro.ini'),os.path.join(dist_folder,'pyro.ini'))
        zip_created: str = self._build_zip_archive(dist_folder)
        print('Wrote archive: %s' % zip_created)

        return 0


if __name__ == '__main__':
    _parser = argparse.ArgumentParser()
    _parser.add_argument('-n', '--python-path', action='store', type=str, default=sys.executable)
    _parser.add_argument('-p', '--package-name', action='store', type=str, default='pyro_cli')
    Application(_parser.parse_args()).run()