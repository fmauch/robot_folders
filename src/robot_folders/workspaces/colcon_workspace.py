import os
import re
import subprocess
import typing

import click
import inquirer
from typeguard import typechecked

from robot_folders.helpers.exceptions import ModuleException
from robot_folders.helpers.ros_version_helpers import installed_ros_2_versions
from robot_folders.workspaces.workspace import Workspace
from robot_folders.helpers import config_helpers


@typechecked
class ColconWorkspace(Workspace):
    def __init__(
        self,
        ws_directory: str,
        build_directory: str,
        ros2_distro: str,
    ):
        super().__init__(ws_directory=ws_directory, build_directory=build_directory)
        self.ros2_distro = ros2_distro
        self.source_directory = os.path.join(ws_directory, "src")

    def create(
        self, repos: typing.Union[str, None], clone_submodules: bool = True
    ) -> None:
        self.__ask_questions()
        self.__create_colcon_skeleton()
        self.build()
        if repos:
            self.clone_packages(repos, clone_submodules)

    def source(self) -> dict[str, str]:
        return os.environ.copy()

    def build(self, **kwargs) -> None:
        click.echo(f"Building colcon_ws in {self.ws_directory}")

        if "colcon_args" in kwargs:
            colcon_args = kwargs["colcon_args"]
            colcon_args = " ".join(colcon_args)
        else:
            colcon_args = config_helpers.get_value_safe_default(
                section="build", value="colcon_build_options", default=""
            )
            cmake_args = config_helpers.get_value_safe_default(
                section="build", value="cmake_flags", default=""
            )
            colcon_args += f" --cmake-args {cmake_args}"

        my_env = self._strip_workspace_from_env(self.source())
        try:
            process = subprocess.check_call(
                ["bash", "-c", "colcon build", colcon_args],
                cwd=self.ws_directory,
                env=my_env,
            )
        except subprocess.CalledProcessError as err:
            raise (ModuleException(err.output, "build_colcon", err.returncode))

    def _strip_workspace_from_env(self, env: dict[str, str]) -> dict[str, str]:
        """
        Removes the colcon workspace from the shell's environment since
        Colcon needs to build in an env that does not have the current workspace sourced
        See https://docs.ros.org/en/galactic/Tutorials/Workspace/Creating-A-Workspace.html#source-the-overlay
        """
        keys_with_colcon_dir = [
            key for key, val in env.items() if self.ws_directory in val
        ]
        for key in keys_with_colcon_dir:
            env[key] = re.sub(self.ws_directory + r"[^:]*", "", env[key])

        return env

    def __ask_questions(self):
        """
        When creating a colcon workspace some questions need to be answered such as which ros
        version to use
        """
        if self.ros2_distro == "ask":
            installed_ros_distros = sorted(installed_ros_2_versions())
            self.ros2_distro = installed_ros_distros[-1]
            if len(installed_ros_distros) > 1:
                questions = [
                    inquirer.List(
                        "ros_distro",
                        message="Which ROS 2 distribution would you like to use for colcon?",
                        choices=installed_ros_distros,
                    ),
                ]
                answer = inquirer.prompt(questions)
                if answer:
                    self.ros2_distro = answer["ros_distro"]
                else:
                    raise RuntimeError("Answer for ROS 2 distro is empty.")
        click.echo("Using ROS 2 distribution '{}'".format(self.ros2_distro))

    def __create_colcon_skeleton(self):
        """
        Creates the workspace skeleton and if necessary the relevant folders for remote build (e.g.
        no_backup)
        """
        # Create directories and symlinks, if necessary
        os.mkdir(self.ws_directory)
        os.mkdir(self.source_directory)
        os.makedirs(self.build_directory)

        local_build_dir_name = os.path.join(self.ws_directory, "build")
        (colcon_base_dir, _) = os.path.split(self.build_directory)

        colcon_log_directory = os.path.join(colcon_base_dir, "log")
        local_log_dir_name = os.path.join(self.ws_directory, "log")
        click.echo("log_dir: {}".format(colcon_log_directory))

        colcon_install_directory = os.path.join(colcon_base_dir, "install")
        local_install_dir_name = os.path.join(self.ws_directory, "install")
        click.echo("install_dir: {}".format(colcon_install_directory))

        if local_build_dir_name != self.build_directory:
            os.symlink(self.build_directory, local_build_dir_name)
            os.makedirs(colcon_log_directory)
            os.symlink(colcon_log_directory, local_log_dir_name)
            os.makedirs(colcon_install_directory)
            os.symlink(colcon_install_directory, local_install_dir_name)
