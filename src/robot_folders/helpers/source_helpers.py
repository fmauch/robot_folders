import os
import subprocess
import sys


def source_bash(
    source_file: str, current_env: dict[str, str] = os.environ.copy()
) -> dict[str, str]:
    if not os.path.exists(source_file):
        raise FileNotFoundError(f"Source file '{source_file}' does not exist.")

    # Basically, this calls sourcing the bash file, printing the environment and then
    # evaluating it to a new environment.
    commands = f"""
    set -a
    source {source_file} > /dev/null
    {sys.executable} -c "import os; print(repr(dict(os.environ)))"
    """
    source_output = subprocess.check_output(
        ["bash", "-c", commands],
        env=current_env,
    )
    sourced_env = eval(source_output)

    return sourced_env
