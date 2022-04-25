from typing import Generator
from urllib.parse import urlparse

from pyro.Comparators import endswith
from pyro.Remotes.RemoteBase import RemoteBase
from pyro.Remotes.BitbucketRemote import BitbucketRemote
from pyro.Remotes.GiteaRemote import GiteaRemote
from pyro.Remotes.GitHubRemote import GitHubRemote


class GenericRemote(RemoteBase):
    def fetch_contents(self, url: str, output_path: str) -> Generator:
        """
        Downloads files from URL to output path
        """
        parsed_url = urlparse(url)

        schemeless_url = url.removeprefix(f'{parsed_url.scheme}://')  # type: ignore

        if endswith(parsed_url.netloc, 'github.com', ignorecase=True):
            if self.config or not self.access_token:  # type: ignore
                self.access_token = self.find_access_token(schemeless_url)
                if not self.access_token:
                    raise PermissionError('Cannot download from GitHub remote without access token')
            github = GitHubRemote(access_token=self.access_token,
                                  worker_limit=self.worker_limit,
                                  force_overwrite=self.force_overwrite)
            yield from github.fetch_contents(url, output_path)
        elif endswith(parsed_url.netloc, 'bitbucket.org', ignorecase=True):
            bitbucket = BitbucketRemote()
            yield from bitbucket.fetch_contents(url, output_path)
        else:
            if self.config or not self.access_token:
                self.access_token = self.find_access_token(schemeless_url)
                if not self.access_token:
                    raise PermissionError('Cannot download from Gitea remote without access token')
            gitea = GiteaRemote(access_token=self.access_token,
                                worker_limit=self.worker_limit,
                                force_overwrite=self.force_overwrite)
            yield from gitea.fetch_contents(url, output_path)
