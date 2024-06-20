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
import pytest

import robot_folders.helpers.ros_version_helpers as ros

from .fixture_ros_installation import fake_ros_installation


@pytest.mark.usefixtures("fake_ros_installation")
def test_installed_ros1_versions():
    assert ros.installed_ros_1_versions() == ["melodic", "noetic"]


@pytest.mark.usefixtures("fake_ros_installation")
def test_installed_ros2_versions():
    assert ros.installed_ros_2_versions() == ["humble", "jazzy", "rolling"]


@pytest.mark.usefixtures("fake_ros_installation")
def test_installed_ros_distros():
    assert ros.installed_ros_distros() == [
        "melodic",
        "noetic",
        "humble",
        "jazzy",
        "rolling",
    ]


def test_ask_ros_distro(mocker):
    mocker.patch("inquirer.prompt", return_value={"ros_distro": "rolling"})

    rosdistro = ros.ask_ros_distro(["humble", "rolling"])
    assert rosdistro == "rolling"


def test_cancelling_ask_ros_distro_raises(mocker):
    mocker.patch("inquirer.prompt", return_value=None)
    with pytest.raises(RuntimeError):
        ros.ask_ros_distro(["humble", "rolling"])
