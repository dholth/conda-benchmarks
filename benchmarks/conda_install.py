import json
import os
import os.path
import pathlib
import re
import tempfile

import conda.core
import conda.misc
from conda.base.context import reset_context
from conda.core.package_cache_data import ProgressiveFetchExtract
from conda.testing.helpers import run_inprocess_conda_command

from .test_server import run_and_cleanup, run_on_random_port

lockfile = pathlib.Path(__file__).parent / "../conda-osx-64.lock"
specs = pathlib.Path(__file__).parent / "../specs.json"  # parsed from lock file


SPECS = json.loads(specs.read_text())


class TimeInstall:
    params = [1, 3, 7, 10]
    param_names = ["threads"]

    def setup(self, threads):
        self.td = tempfile.TemporaryDirectory()
        self.socket = run_on_random_port()

    def teardown(self, threads):
        self.td.cleanup()

    # From remote URLs
    # def time_download_lockfile(self):
    #     os.environ["CONDA_PKGS_DIRS"] = self.td.name
    #     run_inprocess_conda_command(
    #         f"conda install --download-only --file {lockfile}",
    #         disallow_stderr=False,
    #     )

    def time_explicit_install(self, threads):
        socket = self.socket
        prefix = os.path.join(self.td.name, "explicit")
        port = socket.getsockname()[1]
        # requests.get(f"http://127.0.0.1:{self.port}/latency/{latency}")
        specs = [
            re.sub("(.*)(/.*/.*)", f"http://127.0.0.1:{port}\\2", spec)
            for spec in SPECS
        ]
        print(specs)
        os.environ["CONDA_PKGS_DIRS"] = prefix
        reset_context()
        conda.core.package_cache_data.DOWNLOAD_THREADS = threads
        conda.misc.explicit(
            specs,
            prefix,
            verbose=False,
            force_extract=True,
            index_args=None,
            index=None,
        )


if __name__ == "__main__":
    ti = TimeInstall()
    ti.setup(10)
    ti.time_explicit_install(10)
