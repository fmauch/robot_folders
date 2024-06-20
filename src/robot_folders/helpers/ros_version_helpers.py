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
"""Little helper around ROS versions"""

import os
import re

import inquirer


def installed_ros_distros():
    """Returns all installed ROS versions (ROS1 and ROS2)"""
    return installed_ros_1_versions() + installed_ros_2_versions()


def installed_ros_1_versions():
    """Returns a list of all installed ROS1 versions"""
    # Check the setup if it contains catkin the ROS Build system
    temp_installed_ros_distros = os.listdir("/opt/ros")
    installed_ros_distros = []
    for distro in temp_installed_ros_distros:
        if "catkin" in open("/opt/ros/" + distro + "/setup.sh").read():
            installed_ros_distros.append(distro)
    return installed_ros_distros


def installed_ros_2_versions():
    """Returns a list of all installed ROS2 versions"""
    # Check the setup if it contains ament the ROS2 Build system
    temp_installed_ros_distros = os.listdir("/opt/ros")
    installed_ros_distros = []
    for distro in temp_installed_ros_distros:
        source_script_path = os.path.join("/opt/ros", distro, "setup.sh")
        if os.path.isfile(source_script_path):
            with open(source_script_path) as f:
                content = f.read()
                if re.findall("(AMENT_CURRENT_PREFIX|COLCON_CURRENT_PREFIX)", content):
                    installed_ros_distros.append(distro)
    return installed_ros_distros


def ask_ros_distro(options: list[str]) -> str:
    installed_ros_distros = sorted(options)
    distro = installed_ros_distros[-1]
    if len(installed_ros_distros) > 1:
        questions = [
            inquirer.List(
                "ros_distro",
                message="Which ROS distribution would you like to use?",
                choices=installed_ros_distros,
            ),
        ]
        answer = inquirer.prompt(questions)
        print(answer)
        if answer:
            distro = answer["ros_distro"]
        else:
            raise RuntimeError("Answer for ROS distro is empty.")
    return distro
