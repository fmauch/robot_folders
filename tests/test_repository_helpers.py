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

import os
import tempfile

import git
import yaml

import robot_folders.helpers.repository_helpers as repo_helpers


def create_git_repo(repo_path):
    repo = git.Repo.init(repo_path, initial_branch="main")

    update_file = "simple_file.txt"
    with open(os.path.join(repo_path, update_file), "a") as f:
        f.write("\nThis is some content.")
    add_file = [update_file]
    repo.index.add(add_file)
    repo.index.commit("Initial commit")


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
