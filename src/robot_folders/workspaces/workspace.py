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
        self, repos: typing.Union[dict, None], clone_submodules: bool = True
    ) -> None:
        raise NotImplementedError()

    def adapt(
        self,
        repos: typing.Union[dict, None],
        clone_submodules: bool = True,
        local_override_pollicy: str = "ask",
        local_delete_policy: str = "ask",
    ) -> None:
        raise NotImplementedError()

    def scrape(self):
        raise NotImplementedError()

    def build(self) -> None:
        raise NotImplementedError()

    def source(self) -> dict[str, str]:
        raise NotImplementedError()
