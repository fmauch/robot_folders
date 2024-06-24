import os
import re
import subprocess
import typing

import click
from typeguard import typechecked

from robot_folders.helpers import config_helpers, source_helpers
from robot_folders.helpers.exceptions import ModuleException
from robot_folders.helpers.repository_helpers import clone_packages_from_dict
from robot_folders.helpers.ros_version_helpers import (
    ask_ros_distro,
    installed_ros_2_versions,
)
from robot_folders.workspaces.workspace import Workspace


@typechecked
class ColconWorkspace(Workspace):
    def __init__(
        self,
        ws_directory: str,
        build_directory: str,
        ros2_distro: str,  # TODO: This should be moved to create
    ):
        super().__init__(ws_directory=ws_directory, build_directory=build_directory)
        self.ros2_distro = ros2_distro
        self.source_directory = os.path.join(ws_directory, "src")

    def create(
        self, repos: typing.Union[dict, None], clone_submodules: bool = True
    ) -> None:
        self.__ask_questions()
        self.__create_colcon_skeleton()
        os.environ.update(self.source())
        self.build()
        if repos:
            clone_packages_from_dict(
                repos=repos,
                target_dir=self.source_directory,
                clone_submodules=clone_submodules,
            )

    def adapt(
        self, repos: typing.Union[dict, None], clone_submodules: bool = True
    ) -> None:
        click.echo("Adapting colcon workspace")
        raise NotImplementedError()

    def source(self, current_env: dict[str, str] = os.environ.copy()) -> dict[str, str]:
        local_source_file = os.path.join(
            self.ws_directory, "install", "local_setup.bash"
        )

        if os.path.exists(local_source_file):
            return source_helpers.source_bash(
                source_file=local_source_file, current_env=current_env
            )
        self.__get_ros2_distro()
        return source_helpers.source_bash(
            source_file=f"/opt/ros/{self.ros2_distro}/setup.bash",
            current_env=current_env,
        )

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

        my_env = self._strip_workspace_from_env(os.environ.copy())

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
        self.__get_ros2_distro()
        click.echo("Using ROS 2 distribution '{}'".format(self.ros2_distro))

    def __get_ros2_distro(self):
        if self.ros2_distro == "ask":
            self.ros2_distro = ask_ros_distro(installed_ros_2_versions())
        return self.ros2_distro

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
