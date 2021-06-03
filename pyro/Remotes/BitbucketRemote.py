import json
import os
from typing import Generator
from urllib.request import Request
from urllib.request import urlopen

from pyro.Comparators import endswith
from pyro.Remotes.RemoteBase import RemoteBase


class BitbucketRemote(RemoteBase):
    def _fetch_payloads(self, request_url: str) -> Generator:
        """
        Recursively generates payloads from paginated responses
        """
        request = Request(request_url)

        response = urlopen(request, timeout=30)

        if response.status != 200:
            yield 'Failed to load URL (%s): "%s"' % (response.status, request_url)
            return

        payload: dict = json.loads(response.read().decode('utf-8'))

        yield payload

        if 'next' in payload:
            yield from self._fetch_payloads(payload['next'])

    def fetch_contents(self, url: str, output_path: str) -> Generator:
        """
        Downloads files from URL to output path
        """
        owner, repo, request_url = self.extract_request_args(url)

        yield f'Downloading scripts from "{request_url}"... Please wait.'

        script_count: int = 0

        for payload in self._fetch_payloads(request_url):
            for payload_object in payload['values']:
                payload_object_type = payload_object['type']

                target_path = os.path.normpath(os.path.join(output_path, owner, repo, payload_object['path']))

                download_url = payload_object['links']['self']['href']

                if payload_object_type == 'commit_file':
                    # we only care about scripts
                    if not endswith(download_url, '.psc', ignorecase=True):
                        continue

                    file_response = urlopen(download_url, timeout=30)

                    if file_response.status != 200:
                        yield f'Failed to download ({file_response.status}): "{download_url}"'
                        continue

                    os.makedirs(os.path.dirname(target_path), exist_ok=True)

                    with open(target_path, mode='w+b') as f:
                        f.write(file_response.read())

                    script_count += 1

                elif payload_object_type == 'commit_directory':
                    yield from self.fetch_contents(download_url, output_path)

        if script_count > 0:
            yield f'Downloaded {script_count} scripts from "{request_url}"'
