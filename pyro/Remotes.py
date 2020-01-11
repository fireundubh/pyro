import json
import os
from typing import Generator
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class RemoteBase:
    access_token: str = ''

    def __init__(self, access_token: str):
        self.access_token = access_token

    @staticmethod
    def validate_url(url: str) -> bool:
        try:
            result = urlparse(url)
        except HTTPError:
            return False
        else:
            return all([result.scheme, result.netloc, result.path])

    def get_contents(self, url: str, output_path: str) -> Generator:
        pass


class GenericRemote(RemoteBase):
    def get_contents(self, url: str, output_path: str) -> Generator:
        parsed_url = urlparse(url)

        if parsed_url.netloc.endswith('github.com'):
            github = GitHubRemote(self.access_token)
            yield from github.get_contents(url, output_path)
        elif parsed_url.netloc.endswith('bitbucket.org'):
            raise NotImplementedError()
        else:
            raise NotImplementedError()


class GitHubRemote(RemoteBase):
    def get_contents(self, url: str, output_path: str) -> Generator:
        parsed_url = urlparse(url)

        url_path = parsed_url.path[1:]

        if parsed_url.netloc == 'api.github.com':
            request_url = url
            _, owner, repo = url_path.split('/')[:3]
        elif parsed_url.netloc == 'github.com':
            url_path_parts = parsed_url.path.split('/')[1:]
            url_path_parts.pop(3)  # pop 'master' (or any other branch)
            url_path_parts.pop(2)  # pop 'tree'
            url_path_parts.insert(2, 'contents')
            url_path = '/'.join(url_path_parts)
            request_url = f'https://api.github.com/repos/{url_path}'
            owner, repo = url_path_parts[0], url_path_parts[1]
        else:
            raise NotImplementedError

        request = Request(request_url)
        request.add_header('Authorization', f'token {self.access_token}')

        response = urlopen(request, timeout=30)

        if response.status != 200:
            yield 'Failed to load URL (%s): "%s"' % (response.status, request_url)

        payload_objects: list = json.loads(response.read().decode('utf-8'))

        yield f'Downloading {len(payload_objects)} files from "{request_url}"...'

        for payload_object in payload_objects:
            target_path = os.path.normpath(os.path.join(output_path, owner, repo, payload_object['path']))

            download_url = payload_object['download_url']

            # handle folders
            if not download_url:
                yield from self.get_contents(payload_object['url'], output_path)
                continue

            file_response = urlopen(download_url, timeout=30)
            if file_response.status != 200:
                yield f'Failed to download ({file_response.status}): "{payload_object["download_url"]}"'
                continue

            target_folder = os.path.dirname(target_path)
            os.makedirs(target_folder, exist_ok=True)

            with open(target_path, mode='w+b') as f:
                f.write(file_response.read())
