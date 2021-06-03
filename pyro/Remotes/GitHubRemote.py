import json
import multiprocessing
import os
from typing import (Generator,
                    Optional)
from urllib.request import (Request,
                            urlopen)

from pyro.Comparators import endswith
from pyro.Remotes.RemoteBase import RemoteBase


class GitHubRemote(RemoteBase):
    @staticmethod
    def download_file(file: tuple) -> Optional[str]:
        url, target_path = file

        file_response = urlopen(url, timeout=30)

        if file_response.status != 200:
            return f'Failed to download ({file_response.status}): "{url}"'

        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        with open(target_path, mode='w+b') as f:
            f.write(file_response.read())

    def fetch_contents(self, url: str, output_path: str) -> Generator:
        """
        Downloads files from URL to output path
        """
        owner, repo, request_url = self.extract_request_args(url)

        request = Request(request_url)
        request.add_header('Authorization', f'token {self.access_token}')

        response = urlopen(request, timeout=30)

        if response.status != 200:
            yield 'Failed to load URL (%s): "%s"' % (response.status, request_url)
            return

        payload_objects: list = json.loads(response.read().decode('utf-8'))

        yield f'Downloading scripts from "{request_url}"... Please wait.'

        scripts: list = []

        for payload_object in payload_objects:
            target_path = os.path.normpath(os.path.join(output_path, owner, repo, payload_object['path']))

            download_url = payload_object['download_url']

            # handle folders
            if not download_url:
                yield from self.fetch_contents(payload_object['url'], output_path)
                continue

            # we only care about scripts
            if payload_object['type'] != 'file' and not endswith(payload_object['name'], '.psc', ignorecase=True):
                continue

            scripts.append((download_url, target_path))

        script_count: int = len(scripts)

        multiprocessing.freeze_support()
        worker_limit: int = min(script_count, self.worker_limit)
        with multiprocessing.Pool(processes=worker_limit) as pool:
            for download_result in pool.imap_unordered(self.download_file, scripts):
                yield download_result
            pool.close()
            pool.join()

        if script_count > 0:
            yield f'Downloaded {script_count} scripts from "{request_url}"'