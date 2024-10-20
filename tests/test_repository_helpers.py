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

import copy
import os
import shutil
import tempfile

import git
import yaml

import robot_folders.helpers.repository_helpers as repo_helpers


def create_git_repo(repo_path: str) -> git.Repo:
    repo = git.Repo.init(repo_path, initial_branch="main")

    update_file = "simple_file.txt"
    with open(os.path.join(repo_path, update_file), "a") as f:
        f.write("\nThis is some content.")
    add_file = [update_file]
    repo.index.add(add_file)
    repo.index.commit("Initial commit")

    return repo


def test_clone_repos_from_dict():
    repos_storage = tempfile.mkdtemp()
    foo_repo_path = os.path.join(repos_storage, "foo")
    foo_repo = create_git_repo(foo_repo_path)
    data = {
        "repositories": {
            "foo": {"type": "git", "url": foo_repo_path, "version": "main"}
        }
    }

    checkout_dir = tempfile.mkdtemp()
    repo_helpers.clone_packages_from_dict(repos=data, target_dir=checkout_dir)

    assert os.path.exists(os.path.join(checkout_dir, "foo"))
    assert os.path.exists(os.path.join(checkout_dir, "foo", "simple_file.txt"))


def test_clone_repos_from_file():
    repos_storage = tempfile.mkdtemp()
    foo_repo_path = os.path.join(repos_storage, "foo")
    foo_repo = create_git_repo(foo_repo_path)
    data = {
        "repositories": {
            "foo": {"type": "git", "url": foo_repo_path, "version": "main"}
        }
    }

    _, data_filename = tempfile.mkstemp()
    with open(data_filename, "w") as file:
        yaml.dump(data, file)

    checkout_dir = tempfile.mkdtemp()
    repo_helpers.clone_packages_from_repos_file(
        repos_file=data_filename, target_dir=checkout_dir
    )

    assert os.path.exists(os.path.join(checkout_dir, "foo"))
    assert os.path.exists(os.path.join(checkout_dir, "foo", "simple_file.txt"))


def test_find_repos():
    repos_storage = tempfile.mkdtemp()
    foo_repo_path = os.path.join(repos_storage, "foo")
    create_git_repo(foo_repo_path)
    bar_repo_path = os.path.join(repos_storage, "bar")
    create_git_repo(bar_repo_path)

    # Clone repos here:
    ws_src = tempfile.mkdtemp()
    git.Repo.clone_from(foo_repo_path, os.path.join(ws_src, "foo"))
    git.Repo.clone_from(bar_repo_path, os.path.join(ws_src, "bar"))

    repos_parsed = repo_helpers.find_repos_in_path(ws_src)

    for repo_name in repos_parsed.keys():
        repo = repos_parsed[repo_name]
        assert repo["url"] == os.path.join(repos_storage, repo_name)


def test_adapt_additional_repo():
    # Create repo storage
    # repos_storage
    #   ├── foo
    #   ├── bar
    #   ├── bar_fork
    repos_storage = tempfile.mkdtemp()
    foo_repo_path = os.path.join(repos_storage, "foo")
    foo_repo = create_git_repo(foo_repo_path)
    bar_repo_path = os.path.join(repos_storage, "bar")
    bar_repo = create_git_repo(bar_repo_path)
    bar_repo.create_head("develop")
    bar_fork_path = os.path.join(repos_storage, "bar_fork")
    shutil.copytree(bar_repo_path, bar_fork_path)
    bar_fork = git.Repo(bar_fork_path)

    initial_data = {
        "repositories": {
            "foo": {"type": "git", "url": foo_repo_path, "version": "main"}
        }
    }
    additional_data = {
        "repositories": {
            "bar": {"type": "git", "url": bar_repo_path, "version": "main"}
        }
    }
    data_combined = copy.deepcopy(initial_data)
    data_combined["repositories"]["bar"] = copy.deepcopy(
        additional_data["repositories"]["bar"]
    )

    # Create target workspace with foo and bar
    ws_src = tempfile.mkdtemp()
    git.Repo.clone_from(foo_repo_path, os.path.join(ws_src, "foo"))

    # Adapt ws_src containing initial_data to contain all projects from data_combined
    repo_helpers.adapt_repos_from_dict(
        repos_override=data_combined,
        packages_dir=ws_src,
        clone_submodules=True,
        local_override_policy="keep_local",
        local_delete_policy="keep_all",
    )

    assert os.path.exists(os.path.join(ws_src, "bar"))

    bar_cloned = git.Repo(path=os.path.join(ws_src, "bar"))
    assert str(bar_cloned.active_branch) == "main"
    remote_branch = bar_cloned.active_branch.tracking_branch()
    assert remote_branch
    assert bar_cloned.remote(remote_branch.remote_name).url == bar_repo_path

    print(additional_data)
    # Modify repo to adapt
    additional_data["repositories"]["bar"]["url"] = bar_fork_path
    additional_data["repositories"]["bar"]["version"] = "develop"

    # Adapt with different branch, but keep local versions
    repo_helpers.adapt_repos_from_dict(
        repos_override=additional_data,
        packages_dir=ws_src,
        clone_submodules=True,
        local_override_policy="keep_local",
        local_delete_policy="keep_all",
    )
    # Should still be origin with default branch since we used the `keep_Local` override policy
    assert str(bar_cloned.active_branch) == "main"
    remote_branch = bar_cloned.active_branch.tracking_branch()
    assert remote_branch
    assert bar_cloned.remote(remote_branch.remote_name).url == bar_repo_path

    # Same as above but with `override` policy
    repo_helpers.adapt_repos_from_dict(
        repos_override=additional_data,
        packages_dir=ws_src,
        clone_submodules=True,
        local_override_policy="override",
        local_delete_policy="keep_all",
    )
    assert str(bar_cloned.active_branch) == "develop"
    remote_branch = bar_cloned.active_branch.tracking_branch()
    assert remote_branch
    assert bar_cloned.remote(remote_branch.remote_name).url == bar_fork_path

    print("test in question")
    # Remove foo_repo from the adapted workspace, but do not delete local repos
    repo_helpers.adapt_repos_from_dict(
        repos_override=additional_data,
        packages_dir=ws_src,
        clone_submodules=True,
        local_override_policy="keep_local",
        local_delete_policy="keep_all",
    )

    assert os.path.exists(os.path.join(ws_src, "foo"))
    assert os.path.exists(os.path.join(ws_src, "bar"))

    # Remove foo_repo from the adapted workspace and delete local repos
    repo_helpers.adapt_repos_from_dict(
        repos_override=additional_data,
        packages_dir=ws_src,
        clone_submodules=True,
        local_override_policy="keep_local",
        local_delete_policy="delete_all",
    )
    assert not os.path.exists(os.path.join(ws_src, "foo"))
    assert os.path.exists(os.path.join(ws_src, "bar"))
