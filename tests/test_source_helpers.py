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
from tempfile import mkstemp

import pytest

import robot_folders.helpers.source_helpers as source_helpers


def test_source_bash():
    _, source_file = mkstemp()
    original_env = os.environ.copy()
    expected_env = os.environ.copy()
    expected_env["NEW_ENV_VAR"] = "foobihgy"
    with open(source_file, "w") as f:
        f.write(f'export NEW_ENV_VAR={expected_env["NEW_ENV_VAR"]}\n')

    new_env = source_helpers.source_bash(
        source_file=source_file, current_env=original_env
    )

    # Remove keys that are expected to be different
    def remove_key(key):
        if key in new_env:
            new_env.pop(key)
        if key in expected_env:
            expected_env.pop(key)

    remove_key("PS1")
    remove_key("_")
    remove_key("SHLVL")

    assert new_env == expected_env

    with pytest.raises(FileNotFoundError):
        source_helpers.source_bash("/hgf/hfdgh/hdgjhfjh/jhiugibyjiuofasd")
