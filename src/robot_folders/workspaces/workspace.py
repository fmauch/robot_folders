import os
import subprocess
import tempfile
import typing

import yaml
from typeguard import typechecked


@typechecked
class Workspace:
    def __init__(
        self,
        ws_directory: str,
        build_directory: str,
    ):
        self.ws_directory = ws_directory
        self.build_directory = build_directory
        self.source_directory = os.path.join(self.ws_directory, "src")

    def create(
        self, repos: typing.Union[str, None], clone_submodules: bool = True
    ) -> None:
        raise NotImplementedError()

    def build(self) -> None:
        raise NotImplementedError()

    def clone_packages(self, repos_file: str, clone_submodules: bool = True) -> None:
        """
        Clone in packages from a repos file structure
        """

        os.makedirs(self.source_directory, exist_ok=True)
        cmd = ["vcs", "import"]

        if clone_submodules:
            cmd.append("--recursive")
        cmd.extend(
            [
                "--input",
                repos_file,
                self.source_directory,
            ]
        )

        subprocess.check_call(cmd)

    def source(self) -> dict[str, str]:
        raise NotImplementedError()

    def clone_pakages_from_yaml(
        self, repos: str, clone_submodules: bool = True
    ) -> None:
        _, repos_filename = tempfile.mkstemp()
        with open(repos_filename, "w") as repos_file:
            yaml.dump(repos, repos_file)
        self.clone_packages(repos_filename, clone_submodules)
