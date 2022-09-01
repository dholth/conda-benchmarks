import os
import os.path
import pathlib
import tempfile

from conda.testing.helpers import run_inprocess_conda_command

lockfile = pathlib.Path(__file__).parent / "../conda-osx-64.lock"


class TimeInstall:
    def setup(self):
        self.td = tempfile.TemporaryDirectory()

    def teardown(self):
        self.td.cleanup()

    def time_download_lockfile(self):
        os.environ["CONDA_PKGS_DIRS"] = self.td.name
        run_inprocess_conda_command(
            f"conda install --download-only --file {lockfile}",
            disallow_stderr=False,
        )
