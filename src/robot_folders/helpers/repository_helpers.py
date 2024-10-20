#
# Copyright (c) 2024 FZI Forschungszentrum Informatik
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
"""
This module contains helper functions around managing git repositories
"""
import os
import subprocess
import tempfile

import click
import git
import yaml
from vcstool import clients
from vcstool.clients.vcs_base import VcsClientBase
from vcstool.crawler import find_repositories

import robot_folders.helpers.directory_helpers as dir_helpers
from robot_folders.helpers.exceptions import ModuleException
from robot_folders.workspaces import workspace


class VCSCommand:
    def __init__(self):
        self.exact = False


def parse_repository(repo_path, use_commit_id):
    """
    Parses a repository path and returns the remote URL and the version (branch/commit)
    """
    repo = git.Repo(repo_path)
    remotes = repo.remotes
    choice = 0

    detached_head = repo.head.is_detached

    if len(remotes) > 1:
        click.echo("Found multiple remotes for repo {}.".format(repo_path))
        upstream_remote = None
        if not detached_head:
            upstream_branch = repo.active_branch.tracking_branch()
            if upstream_branch == None:
                raise ModuleException(
                    'Branch "{}" from repository "{}" does not have a tracking branch configured. Cannot scrape environment.'.format(
                        repo.active_branch, repo_path
                    ),
                    "repository_helpers",
                    1,
                )

            upstream_remote = upstream_branch.name.split("/")[0]
        default = None
        for index, remote in enumerate(remotes):
            click.echo("{}: {} ({})".format(index, remote.name, remote.url))
            if remote.name == upstream_remote:
                default = index
        valid_choice = -1
        while valid_choice < 0:
            choice = click.prompt(
                "Which one do you want to use?",
                type=int,
                default=default,
                show_default=True,
            )
            if choice >= 0 and choice < len(remotes):
                valid_choice = choice
            else:
                click.echo("Invalid choice: '{}'".format(choice))
        click.echo(
            "Selected remote {} ({})".format(remotes[choice].name, remotes[choice].url)
        )
    url = remotes[choice].url

    if detached_head or use_commit_id:
        version = repo.head.commit.hexsha
    else:
        version = repo.active_branch.name
    return url, version


def create_rosinstall_entry(repo_path, local_name, use_commit_id=False):
    """
    Creates a rosinstall dict entry for a given repo path and local folder name
    """
    repo = dict()
    repo["git"] = dict()
    repo["git"]["local-name"] = local_name

    url, version = parse_repository(repo_path, use_commit_id)
    repo["git"]["uri"] = url
    repo["git"]["version"] = version
    return repo


def clone_packages_from_repos_file(
    repos_file: str, target_dir: str, clone_submodules: bool = True
) -> None:
    """
    Clone in packages from a repos file structure
    """

    os.makedirs(target_dir, exist_ok=True)
    cmd = ["vcs", "import"]

    if clone_submodules:
        cmd.append("--recursive")
    cmd.extend(
        [
            "--input",
            repos_file,
            target_dir,
        ]
    )

    subprocess.check_call(cmd)


def clone_packages_from_dict(
    repos: dict, target_dir: str, clone_submodules: bool = True
) -> None:
    _, repos_filename = tempfile.mkstemp()
    with open(repos_filename, "w") as repos_file:
        yaml.dump(repos, repos_file)
    clone_packages_from_repos_file(repos_filename, target_dir, clone_submodules)


def parse_repo(repo: VcsClientBase, basename: str, exact: bool) -> tuple[str, dict]:
    command = VCSCommand()
    command.exact = exact

    parsed = {}
    rel_path = os.path.relpath(path=repo.path, start=basename)
    parsed["type"] = repo.__class__.type
    export_data = repo.export(command=command)["export_data"]
    parsed["url"] = export_data["url"]
    parsed["version"] = export_data["version"]
    return (rel_path, parsed)


def find_repos_in_path(
    target_path: str, nested: bool = True, exact: bool = False
) -> dict:
    repos_found = find_repositories([target_path], nested=nested)

    ret = {}
    for repo in repos_found:
        entry = parse_repo(repo, target_path, exact)
        ret[entry[0]] = entry[1]

    return ret


def adapt_repos_from_dict(
    repos_override: dict,
    packages_dir: str,
    clone_submodules: bool = True,
    local_override_policy: str = "ask",
    local_delete_policy: str = "ask",
):
    """
    Parses the given repos_overwrite and compares it to the packages in repos.
    """
    repos = find_repos_in_path(packages_dir)
    for repo_name in repos_override["repositories"].keys():
        print(f"checking '{repo_name}'")
        repo = repos_override["repositories"][repo_name]
        local_version_exists = False
        version_update_required = True
        url_update_required = True
        url = ""
        version = ""

        package_dir = os.path.join(packages_dir, repo_name)

        if repo["type"] != "git":
            click.echo(
                f"Repo {repo_name} has type {repo['type']}. Currently, only the type 'git' is supported. Skipping package."
            )
            continue

        if "version" in repo:
            version = repo["version"]
        else:
            click.echo(
                "WARNING: No version tag given for package '{}'. "
                "The local version will be kept or the default branch "
                "will be checked out for new package".format(repo_name)
            )

        if "url" in repo:
            url = repo["url"]
        else:
            click.echo(
                "WARNING: No url given for package '{}'. "
                "Skipping package".format(repo_name)
            )
            continue

        # compare the repos' versions and uris
        if repo_name in repos.keys():
            local_version_exists = True
            local_repo = repos[repo_name]
            print(local_repo)
            version_update_required = False
            if version != "" and version != local_repo["version"]:
                click.echo(
                    f"Package '{repo_name}' version '{version}' differs from local version '{local_repo['version']}'. "
                )

                if local_override_policy == "keep_local":
                    click.echo(
                        f"Going to keep the local version '{local_repo['version']}'"
                    )
                    version_update_required = False
                elif local_override_policy == "override":
                    click.echo(f"Going to use the updated version '{version}'")
                    version_update_required = True
                else:
                    click.echo("Which version should be used?")
                    click.echo("1) local version: {}".format(local_repo["version"]))
                    click.echo("2) config_file version: {}".format(version))
                    version_to_keep = click.prompt(
                        "Which version should be used?",
                        type=click.Choice(["1", "2"]),
                        default="1",
                    )
                    version_update_required = version_to_keep == "2"

            if url == local_repo["url"]:
                url_update_required = False
            elif local_override_policy == "keep_local":
                url_update_required = False
            elif local_override_policy == "override":
                url_update_required = True
            else:
                click.echo(
                    "Package '{}' url differs from local version. ".format(repo_name)
                )
                click.echo("local version: {}".format(local_repo["url"]))
                click.echo("config_file version: {}".format(url))
                version_to_keep = click.prompt(
                    "Which url should be used?",
                    type=click.Choice(["1", "2"]),
                    default="2",
                )
                url_update_required = version_to_keep == "2"

        else:
            click.echo(
                "Package '{}' does not exist in local structure. "
                "Going to download.".format(repo_name)
            )

        # Create repo if it does not exist yet.
        if not local_version_exists:
            if clone_submodules:
                subprocess.check_call(
                    ["git", "clone", url, package_dir, "--recurse-submodules"]
                )
            else:
                subprocess.check_call(["git", "clone", url, package_dir])

        # Change the origin to the url specified
        if url_update_required:
            subprocess.check_call(
                ["git", "remote", "set-url", "origin", url], cwd=package_dir
            )

        # Checkout the version specified
        if version_update_required:
            subprocess.check_call(["git", "fetch"], cwd=package_dir)
            subprocess.check_call(["git", "checkout", version], cwd=package_dir)

    for local_name in repos.keys():
        if local_name not in repos_override["repositories"].keys():
            click.echo(
                "Package '{}' found locally, but not in target config.".format(
                    local_name
                )
            )
            package_dir = os.path.join(packages_dir, local_name)
            if local_delete_policy == "delete_all":
                dir_helpers.recursive_rmdir(package_dir)
                click.echo("Deleted '{}'".format(local_name))
            elif local_delete_policy == "ask":
                if click.confirm("Do you want to delete it?"):
                    dir_helpers.recursive_rmdir(package_dir)
                    click.echo("Deleted '{}'".format(local_name))
            elif local_delete_policy == "keep_all":
                click.echo("Keeping repository as all should be kept")
