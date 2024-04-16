from pathlib import Path
import shutil
from typing import Optional
from urllib.parse import urlsplit, quote

from racetrack_commons.dir import project_root
from racetrack_client.log.context_error import wrap_context, ContextError
from racetrack_client.client_config.client_config import Credentials
from racetrack_client.manifest import Manifest
from racetrack_client.utils.shell import shell, CommandError, shell_output


def fetch_repository(workspace: Path, manifest: Manifest, git_credentials: Optional[Credentials]) -> tuple[Path, str]:
    """Clone git repository to local workspace directory and return fetched project path"""
    remote_url = git_remote_with_credentials(manifest.git.remote, git_credentials)

    with wrap_context('cloning git repo'):
        try:
            if manifest.git.branch:
                assert '"' not in manifest.git.branch, 'illegal characters in a branch name'
            branch_cmd = f'--branch "{manifest.git.branch}"' if manifest.git.branch else ''
            cmd = f'GIT_TERMINAL_PROMPT=0 git clone --depth=1 --single-branch {branch_cmd} "{remote_url}" "{workspace.resolve()}"'
            shell(cmd, workdir=project_root(), print_log=False)
        except CommandError as e:
            if 'fatal: Authentication failed' in e.stdout:
                if git_credentials is None:
                    raise RuntimeError('no git credentials configured for a repo') from e
                raise ContextError('authentication failure') from e
            raise e

    git_version = read_job_git_version(workspace)
    shutil.rmtree((workspace / '.git').resolve())  # exclude .git from the job image

    assert workspace.is_dir(), f'workspace directory doesn\'t exist: {workspace}'
    sub_workspace = (workspace / manifest.git.directory).resolve()
    assert sub_workspace.is_dir(), f"can't find workspace subdirectory: {sub_workspace}"
    return sub_workspace, git_version


def read_job_git_version(workspace: Path) -> str:
    """Read version from job git history"""
    with wrap_context('reading version from job git history'):
        git_version = shell_output('git describe --long --tags --dirty --always', workdir=workspace).strip()
        return git_version


def git_remote_with_credentials(remote_url: str, credentials: Optional[Credentials]) -> str:
    """Add credentials to git remote URL if configured"""
    if credentials is None:
        credentials = Credentials(username='', password='')

    split = urlsplit(remote_url)
    if not split.scheme:
        return remote_url
    return f'{split.scheme}://{quote(credentials.username)}:{quote(credentials.password)}@{split.netloc}{split.path}'
