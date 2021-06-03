import configparser
import os
from typing import Generator, Optional
from urllib.error import HTTPError
from urllib.parse import urlparse


class RemoteBase:
    access_token: str = ''

    def __init__(self, *, config: configparser.ConfigParser = None, access_token: str = '', worker_limit: int = -1) -> None:
        self.config = config
        self.access_token = access_token
        self.worker_limit = worker_limit

    @staticmethod
    def create_local_path(url: str) -> str:
        """
        Creates relative local path from URL
        """
        parsed_url = urlparse(url)

        netloc = parsed_url.netloc

        url_path_parts = parsed_url.path.split('/')
        url_path_parts.pop(0)  # pop empty space

        url_patterns: dict = {
            'api.github.com': (3, 0),           # pop 'contents', 'repos'
            'github.com': (3, 2),               # pop branch, 'tree'
            'api.bitbucket.org': (5, 4, 1, 0),  # pop branch, 'src', 'repositories', '2.0'
            'bitbucket.org': (3, 2)             # pop branch, 'src'
        }

        for i in url_patterns[netloc]:
            url_path_parts.pop(i)

        url_path = os.sep.join(url_path_parts)

        return url_path

    @staticmethod
    def extract_request_args(url: str) -> tuple:
        """
        Extracts (owner, repo, request_url) from URL
        """
        parsed_url = urlparse(url)

        url_path_parts = parsed_url.path.split('/')
        url_path_parts.pop(0)  # pop empty space

        if parsed_url.netloc == 'api.github.com':
            url_path_parts.pop(0)  # pop 'repos'
            request_url = url
        elif parsed_url.netloc == 'github.com':
            branch = url_path_parts.pop(3)  # pop 'master' (or any other branch)
            url_path_parts.pop(2)  # pop 'tree'
            url_path_parts.insert(2, 'contents')
            url_path = '/'.join(url_path_parts)
            request_url = f'https://api.github.com/repos/{url_path}?ref={branch}'
        elif parsed_url.netloc == 'api.bitbucket.org':
            request_url = url
        elif parsed_url.netloc == 'bitbucket.org':
            request_url = f'https://api.bitbucket.org/2.0/repositories{parsed_url.path}{parsed_url.query}'
        else:
            raise NotImplementedError

        owner, repo = url_path_parts[0], url_path_parts[1]

        return owner, repo, request_url

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


