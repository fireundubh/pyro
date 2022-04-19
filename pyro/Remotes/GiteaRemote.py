import hashlib
import json
import multiprocessing
import os
import sys
import urllib.error
from http import HTTPStatus
from typing import (Generator,
                    Optional,
                    Union)
from urllib.request import (Request,
                            urlopen)

from pyro.Comparators import endswith
from pyro.Remotes.RemoteBase import RemoteBase


class GiteaRemote(RemoteBase):
    @staticmethod
    def download_file(file: tuple) -> Optional[str]:
        url, target_path = file

        file_response = urlopen(url, timeout=30)

        if file_response.status != 200:
            return f'Failed to download ({file_response.status}): "{url}"'

        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        with open(target_path, mode='wb') as f:
            f.write(file_response.read())

        return None

    def fetch_contents(self, url: str, output_path: str) -> Generator:
        """
        Downloads files from URL to output path
        """
        request_url = self.extract_request_args(url)

        request = Request(request_url.url)
        request.add_header('Authorization', f'token {self.access_token}')

        try:
            response = urlopen(request, timeout=30)
        except urllib.error.HTTPError as e:
            status: HTTPStatus = HTTPStatus(e.code)
            yield 'Failed to load remote: "%s" (%s %s)' % (request_url.url, e.code, status.phrase)
            sys.exit(1)

        if response.status != 200:
            status: HTTPStatus = HTTPStatus(response.status)  # type: ignore
            yield 'Failed to load remote: "%s" (%s %s)' % (request_url.url, response.status, status.phrase)
            sys.exit(1)

        payload_objects: Union[dict, list] = json.loads(response.read().decode('utf-8'))

        scripts: list = []

        for payload_object in payload_objects:
            target_path = os.path.normpath(os.path.join(output_path, request_url.owner, request_url.repo, payload_object['path']))

            if not self.force_overwrite and os.path.isfile(target_path):
                with open(target_path, mode='rb') as f:
                    data = f.read()
                    sha1 = hashlib.sha1(b'blob %s\x00%s' % (len(data), data.decode()))  # type: ignore

                    if sha1.hexdigest() == payload_object['sha']:
                        continue

            download_url = payload_object['download_url']

            # handle folders
            if not download_url:
                yield from self.fetch_contents(payload_object['url'], output_path)
                continue

            # we only care about scripts and flags files
            if not (payload_object['type'] == 'file' and endswith(payload_object['name'], ('.flg', '.psc'), ignorecase=True)):
                continue

            scripts.append((download_url, target_path))

        script_count: int = len(scripts)

        if script_count == 0:
            return

        multiprocessing.freeze_support()
        worker_limit: int = min(script_count, self.worker_limit)
        with multiprocessing.Pool(processes=worker_limit) as pool:
            for download_result in pool.imap_unordered(self.download_file, scripts):
                yield download_result
            pool.close()
            pool.join()

        if script_count > 0:
            yield f'Downloaded {script_count} scripts from "{request_url.url}"'
