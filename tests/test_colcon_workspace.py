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
import subprocess
import sys
import tempfile

import pytest

import robot_folders.workspaces.colcon_workspace as ws

from .fixture_ros_installation import fake_ros_installation
from .test_repository_helpers import create_git_repo


# @pytest.mark.usefixtures("fake_ros_installation")
def test_create_colcon_ws(mocker, fs):
    mocker.patch("subprocess.check_call")
    mocker.patch(
        "subprocess.check_output",
        return_value="{'AMENT_PREFIX_PATH':'/opt/ros/rolling'}",
    )
    env = tempfile.mkdtemp()
    print(env)
    fs.create_file("/opt/ros/rolling/setup.bash")
    ws_root = os.path.join(env, "colcon_ws")
    ws_src = os.path.join(ws_root, "src")
    my_ws = ws.ColconWorkspace(
        ws_directory=ws_root,
        build_directory=os.path.join(ws_root, "build"),
        ros2_distro="rolling",
    )
    my_ws.create(repos=None)

    assert os.path.isdir(ws_src)
    assert os.environ["AMENT_PREFIX_PATH"] == "/opt/ros/rolling"

    subprocess.check_call.assert_called_once_with(
        [
            "bash",
            "-c",
            "colcon build",
            "--symlink-install --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=1",
        ],
        cwd=ws_root,
        env=os.environ.copy(),
    )


def test_ws_strip_source():
    orig_env = os.environ.copy()
    orig_env["AMENT_PREFIX_PATH"] = f":/foo/bar/other"

    ws_root = os.path.join("/foo/foo", "colcon_ws")
    ws_src = os.path.join(ws_root, "src")
    my_ws = ws.ColconWorkspace(
        ws_directory=ws_root,
        build_directory=os.path.join(ws_root, "build"),
        ros2_distro="rolling",
    )

    env = copy.deepcopy(orig_env)
    env["AMENT_PREFIX_PATH"] = f"{os.path.join(ws_src, 'foo_package')}:/foo/bar/other"

    sourced_env = my_ws._strip_workspace_from_env(env)
    assert orig_env == sourced_env


def test_ws_source_unbuilt():
    if not os.path.exists("/opt/ros/rolling/setup.bash"):
        pytest.skip("Skipping test due to non-existing rolling installation")
    ws_root = os.path.join("/foo/foo", "colcon_ws")
    my_ws = ws.ColconWorkspace(
        ws_directory=ws_root,
        build_directory=os.path.join(ws_root, "build"),
        ros2_distro="rolling",
    )
    env = my_ws.source()


def test_adapt(mocker):
    mocker.patch(
        "subprocess.check_output",
        return_value="{'AMENT_PREFIX_PATH':'/opt/ros/rolling'}",
    )
    env = tempfile.mkdtemp()
    ws_root = os.path.join(env, "colcon_ws")
    ws_src = os.path.join(ws_root, "src")
    my_ws = ws.ColconWorkspace(
        ws_directory=ws_root,
        build_directory=os.path.join(ws_root, "build"),
        ros2_distro="rolling",
    )

    repos_storage = tempfile.mkdtemp()
    foo_repo_path = os.path.join(repos_storage, "foo")
    foo_repo = create_git_repo(foo_repo_path)
    bar_repo_path = os.path.join(repos_storage, "bar")
    bar_repo = create_git_repo(bar_repo_path)

    base_rosinstall = {
        "repositories": {
            "foo": {"type": "git", "url": foo_repo_path, "version": "main"}
        }
    }
    my_ws.create(repos=base_rosinstall)

    additional_rosinstall = {
        "repositories": {
            "bar": {"type": "git", "url": bar_repo_path, "version": "main"}
        }
    }
    my_ws.adapt(additional_rosinstall)

    assert os.path.exists(os.path.join(ws_src, "foo", "simple_file.txt"))
    # assert os.path.exists(os.path.join(ws_src, "bar", "simple_file.txt"))
