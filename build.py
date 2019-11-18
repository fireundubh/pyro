import sys
from argparse import ArgumentParser, Namespace
from glob import glob
from os import makedirs, remove
from os.path import dirname, exists, isfile, join, normpath, relpath
from shutil import copy2, rmtree
from subprocess import check_call, CalledProcessError
from zipfile import ZIP_STORED, ZipFile


class Application:
    def __init__(self, args: Namespace) -> None:
        self.root_path: str = dirname(__file__)
        print('Using path to project: "%s"' % self.root_path)

        self.package_name = args.package_name
        self.loose = args.loose
        self.mingw64 = args.mingw64

        self.dist_path = join(self.root_path, '%s.dist' % self.package_name)
        self.root_tools_path = join(self.root_path, 'tools')
        self.dist_tools_path = join(self.dist_path, 'tools')

    def __setattr__(self, key: str, value: str) -> None:
        # sanitize paths
        if key.endswith('path'):
            value = normpath(value)
            # normpath converts empty paths to os.curdir which we don't want
            if value == '.':
                value = ''
        super(Application, self).__setattr__(key, value)

    def _clean_dist_folder(self) -> None:
        if not exists(self.dist_path):
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

        files = [f for f in glob(join(self.dist_path, '**\*'), recursive=True)
                 if isfile(f) and not f.endswith(files_to_keep)]

        for f in files:
            remove(f)
            print('Deleted: %s' % f)

        site_dir = join(self.dist_path, 'site')
        if exists(site_dir):
            rmtree(site_dir, ignore_errors=True)

    def _build_zip_archive(self) -> str:
        zip_path: str = join(self.root_path, 'bin', '%s.zip' % self.package_name)
        makedirs(dirname(zip_path), exist_ok=True)

        files = [f for f in glob(join(self.dist_path, '**\*'), recursive=True) if isfile(f)]

        with ZipFile(zip_path, 'w', compression=ZIP_STORED) as z:
            for f in files:
                z.write(f, join(self.package_name, relpath(f, self.dist_path)), compress_type=ZIP_STORED)
                print('Added file to archive: %s' % f)

        return zip_path

    def run(self) -> int:
        print('Cleaning: %s' % self.dist_path)
        if exists(self.dist_path):
            rmtree(self.dist_path, ignore_errors=True)

        # noinspection PyListCreation
        args: list = [
            'pipenv',
            'run',
            'nuitka',
            '--standalone', 'pyro',
            '--include-package=pyro',
            '--experimental=use_pefile',
            '--python-flag=nosite',
            '--python-for-scons=%s' % sys.executable,
            '--assume-yes-for-downloads',
            '--plugin-enable=multiprocessing',
            '--show-progress',
            '--file-reference-choice=runtime'
        ]

        if self.mingw64:
            args.append('--mingw64')

        print('Executing command: %s' % ' '.join(args))
        try:
            check_call(args)
        except CalledProcessError as e:
            print('Failed to execute command: %s' % e.cmd)
            print('Resetting: %s' % self.dist_path)
            if exists(self.dist_path):
                rmtree(self.dist_path, ignore_errors=True)
            return e.returncode

        print('Removing unnecessary files...')
        self._clean_dist_folder()

        print('Copying tools...')
        makedirs(self.dist_tools_path, exist_ok=True)
        for f in ('bsarch.exe', 'bsarch.license.txt'):
            copy2(join(self.root_tools_path, f), join(self.dist_tools_path, f))

        if not self.loose:
            print('Building archive...')
            zip_created: str = self._build_zip_archive()
            print('Wrote archive: %s' % zip_created)

        return 0


if __name__ == '__main__':
    _parser = ArgumentParser()
    _parser.add_argument('-p', '--package-name', action='store', type=str, default='pyro')
    _parser.add_argument('--loose', action='store_true', default=False)
    _parser.add_argument('--mingw64', action='store_true', default=False)
    Application(_parser.parse_args()).run()
