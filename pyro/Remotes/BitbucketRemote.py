import json
import os
import sys
import urllib.error
from collections.abc import Generator
from http import HTTPStatus
from typing import cast
from urllib.request import Request
from urllib.request import urlopen

from pyro.Comparators import endswith
from pyro.Remotes.RemoteBase import RemoteBase

# Type alias for JSON payload from Bitbucket API
type JsonPayload = dict[str, 'JsonValue']
type JsonValue = str | int | float | bool | None | list['JsonValue'] | JsonPayload


class BitbucketRemote(RemoteBase):
    def _fetch_payloads(self, request_url: str) -> Generator[JsonPayload, None, None]:
        """
        Recursively generates payloads from paginated responses
        """
        request = Request(request_url)

        try:
            response = urlopen(request, timeout=30)
        except urllib.error.HTTPError as e:
            status: HTTPStatus = HTTPStatus(e.code)
            BitbucketRemote.log.error('Failed to load remote: "%s" (%s %s)' % (request_url, e.code, status.phrase))
            sys.exit(1)

        if response.status != 200:
            status = HTTPStatus(response.status)
            BitbucketRemote.log.error('Failed to load remote: "%s" (%s %s)' % (request_url, response.status, status.phrase))
            sys.exit(1)

        payload: JsonPayload = json.loads(response.read().decode('utf-8'))

        yield payload

        if 'next' in payload:
            next_url = payload['next']
            if isinstance(next_url, str):
                yield from self._fetch_payloads(next_url)

    def fetch_contents(self, url: str, output_path: str) -> Generator[str | None, None, None]:
        """
        Downloads files from URL to output path
        """
        request_url = self.extract_request_args(url)

        script_count: int = 0

        for payload in self._fetch_payloads(request_url.url):
            values = payload.get('values')
            if not isinstance(values, list):
                continue

            for payload_object in values:
                if not isinstance(payload_object, dict):
                    continue

                payload_object_type = payload_object.get('type')
                path_value = payload_object.get('path')
                links = payload_object.get('links')

                if not isinstance(path_value, str) or not isinstance(links, dict):
                    continue

                self_link = links.get('self')
                if not isinstance(self_link, dict):
                    continue

                download_url = self_link.get('href')
                if not isinstance(download_url, str):
                    continue

                target_path = os.path.normpath(os.path.join(output_path, request_url.owner, request_url.repo, path_value))

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
            yield f'Downloaded {script_count} scripts from "{request_url.url}"'
