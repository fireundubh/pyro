import hashlib
import json
import multiprocessing
import os
import sys
import urllib.error
from collections.abc import Generator
from http import HTTPStatus
from typing import TypedDict
from urllib.request import (Request,
                            urlopen)

from pyro.Comparators import endswith
from pyro.Remotes.RemoteBase import RemoteBase


class _GitHubRepoPayload(TypedDict, total=False):
    contents_url: str
    default_branch: str


class _GitHubFilePayload(TypedDict, total=False):
    path: str
    sha: str
    download_url: str | None
    url: str
    type: str
    name: str


class GitHubRemote(RemoteBase):
    @staticmethod
    def download_file(file: tuple[str, str]) -> str | None:
        url, target_path = file

        file_response = urlopen(url, timeout=30)

        if file_response.status != 200:
            return f'Failed to download ({file_response.status}): "{url}"'

        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        with open(target_path, mode='wb') as f:
            f.write(file_response.read())

        return None

    def fetch_contents(self, url: str, output_path: str) -> Generator[str | None, None, None]:
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
            status = HTTPStatus(response.status)
            yield 'Failed to load remote: "%s" (%s %s)' % (request_url.url, response.status, status.phrase)
            sys.exit(1)

        raw_payload = json.loads(response.read().decode('utf-8'))

        # Handle repo-level response (has contents_url)
        if isinstance(raw_payload, dict) and 'contents_url' in raw_payload:
            branch = str(raw_payload.get('default_branch', ''))
            contents_url = str(raw_payload.get('contents_url', '')).replace('{+path}', f'?ref={branch}')
            yield from self.fetch_contents(contents_url, output_path)
            return

        # Handle file listing response
        payload_objects: list[_GitHubFilePayload] = raw_payload if isinstance(raw_payload, list) else []

        scripts: list[tuple[str, str]] = []

        for payload_object in payload_objects:
            path_value = payload_object.get('path', '')
            target_path = os.path.normpath(os.path.join(output_path, request_url.owner, request_url.repo, path_value))

            if not self.force_overwrite and os.path.isfile(target_path):
                with open(target_path, mode='rb') as f:
                    data = f.read()
                    sha1 = hashlib.sha1(b'blob %d\x00' % len(data) + data)

                    if sha1.hexdigest() == payload_object.get('sha'):
                        continue

            download_url = payload_object.get('download_url')

            # handle folders
            if not download_url:
                url_value = payload_object.get('url', '')
                yield from self.fetch_contents(url_value, output_path)
                continue

            # we only care about scripts and flags files
            name_value = payload_object.get('name', '')
            if not (payload_object.get('type') == 'file' and endswith(name_value, ('.flg', '.psc'), ignorecase=True)):
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
