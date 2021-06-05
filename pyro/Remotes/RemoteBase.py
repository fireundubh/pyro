import configparser
import os
from typing import Generator, Optional
from urllib.error import HTTPError
from urllib.parse import urlparse

from pyro.Comparators import startswith
from pyro.Remotes.RemoteUri import RemoteUri


class RemoteBase:
    access_token: str = ''

    url_patterns: dict = {
        'api.github.com': (3, 0),  # pop 'contents', 'repos'
        'github.com': (3, 2),  # pop branch, 'tree'
        'api.bitbucket.org': (5, 4, 1, 0),  # pop branch, 'src', 'repositories', '2.0'
        'bitbucket.org': (3, 2)  # pop branch, 'src'
    }

    def __init__(self, *, config: configparser.ConfigParser = None, access_token: str = '', worker_limit: int = -1, force_overwrite: bool = False) -> None:
        self.config = config
        self.access_token = access_token
        self.worker_limit = worker_limit
        self.force_overwrite = force_overwrite

    def create_local_path(self, url: str) -> str:
        """
        Creates relative local path from URL
        """
        parsed_url = urlparse(url)

        netloc = parsed_url.netloc

        url_path_parts = parsed_url.path.split('/')
        url_path_parts.pop(0) if not url_path_parts[0] else None  # pop empty space

        if netloc == 'github.com' and len(url_path_parts) == 2:
            return os.sep.join(url_path_parts)

        for i in self.url_patterns[netloc]:
            url_path_parts.pop(i)

        url_path = os.sep.join(url_path_parts)

        return url_path

    @staticmethod
    def extract_request_args(url: str) -> RemoteUri:
        """
        Extracts (owner, repo, request_url) from URL
        """
        result = RemoteUri()

        data = urlparse(url)

        # remove '.git' from clone url, if suffix exists
        result.data = data._asdict()
        result.data['path'] = result.data['path'].replace('.git', '')

        netloc, path, query = result.data['netloc'], result.data['path'], result.data['query']

        # store branch if specified
        query_params = query.split('&')
        for param in query_params:
            if startswith(param, 'ref', ignorecase=True):
                _, branch = param.split('=')
                result.branch = branch
                break

        url_path_parts = path.split('/')
        url_path_parts.pop(0) if not url_path_parts[0] else None  # pop empty space

        request_url = ''

        if netloc == 'github.com':
            if len(url_path_parts) == 2:
                request_url = 'https://api.github.com/repos{}'.format(path)
            elif 'tree/' in path:  # example: /fireundubh/LibFire/tree/master
                result.branch = url_path_parts.pop(3)  # pop 'master' (or any other branch)
                url_path_parts.pop(2) if url_path_parts[2] == 'tree' else None  # pop 'tree'
                url_path_parts.insert(2, 'contents')
                url_path = '/'.join(url_path_parts)
                request_url = f'https://api.github.com/repos/{url_path}?ref={result.branch}'
        elif netloc == 'api.github.com':
            if startswith(path, '/repos'):
                url_path_parts.pop() if not url_path_parts[len(url_path_parts) - 1] else None  # pop empty space
                url_path_parts.pop() if url_path_parts[len(url_path_parts) - 1] == 'contents' else None  # pop 'contents'
                url_path_parts.pop(0)  # pop 'repos'
                request_url = url
        elif netloc == 'bitbucket.org':
            request_url = 'https://api.bitbucket.org/2.0/repositories{}{}'.format(path, query)
        elif netloc == 'api.bitbucket.org':
            request_url = url
        else:
            raise NotImplementedError

        result.owner = url_path_parts[0]
        result.repo = url_path_parts[1]
        result.url = request_url

        return result

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Tests whether URL has scheme, netloc, and path
        """
        try:
            result = urlparse(url)
        except HTTPError:
            return False
        else:
            return all([result.scheme, result.netloc, result.path])

    def find_access_token(self, schemeless_url: str) -> Optional[str]:
        if self.config:
            for section_url in self.config.sections():
                if section_url.casefold() in schemeless_url.casefold():
                    token = self.config.get(section_url, 'access_token', fallback=None)
                    if token:
                        return os.path.expanduser(os.path.expandvars(token))
        return None

    def fetch_contents(self, url: str, output_path: str) -> Generator:
        """
        Downloads files from URL to output path
        """
        pass
