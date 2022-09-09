import contextlib
import json
import logging
import os
import os.path
import pathlib
import re
import subprocess
import tempfile
import time
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial

import conda
import conda.core
import conda.core.package_cache_data
import conda.misc
import conda_package_streaming.extract
import requests
from conda.base.context import context, reset_context
from conda.core.package_cache_data import ProgressiveFetchExtract
from conda.exports import download
from conda.testing.helpers import run_inprocess_conda_command

from benchmarks.test_server import run_and_cleanup, run_on_random_port

log = logging.getLogger(__name__)

lockfile = pathlib.Path(__file__).parent / "../conda-osx-64.lock"
specs = pathlib.Path(__file__).parent / "../specs.json"  # parsed from lock file


SPECS = json.loads(specs.read_text())


class TimeInstall:
    params = [[1, 3, 7], [0.0, 0.25]]
    param_names = ["threads", "latency"]

    def setup(self, threads, latency, server=True):
        self.td = tempfile.TemporaryDirectory()
        if server:
            self.socket = run_on_random_port()

    def teardown(self, threads, latency):
        self.td.cleanup()

    # From remote URLs
    # def time_download_lockfile(self):
    #     os.environ["CONDA_BASE"] = self.td.name
    #     os.environ["CONDA_PKGS_DIRS"] = self.td.name
    #     print(f"Download to {self.td.name}")
    #     reset_context()
    #     run_inprocess_conda_command(
    #         f"conda install --download-only --file {lockfile}",
    #         disallow_stderr=False,
    #     )

    def time_explicit_install(self, threads, latency, download_only=True):
        socket = self.socket
        prefix = os.path.join(self.td.name, f"ex-{threads}-{latency}")
        port = socket.getsockname()[1]
        requests.get(f"http://127.0.0.1:{port}/latency/{latency}")
        specs = [
            re.sub("(.*)(/.*/.*)", f"http://127.0.0.1:{port}\\2", spec)
            for spec in SPECS
        ]
        log.debug("%s", specs)
        os.environ["CONDA_PKGS_DIRS"] = prefix
        reset_context()
        print(f"threads={threads}")
        conda.core.package_cache_data.DOWNLOAD_THREADS = threads
        context.download_only = download_only
        context.debug = 1
        try:
            conda.misc.explicit(
                specs,
                prefix,
                verbose=False,
                force_extract=True,
                index_args=None,
                index=None,
            )
        except conda.CondaExitZero:
            log.info("cache prepared (not an error)")


@contextlib.contextmanager
def timeme(message=""):
    t = time.monotonic()
    yield
    print(f"{message}Took {time.monotonic()-t:0.2f}s")


def run():
    for latency in (10.0,):
        for threads in (1, 3, 10):
            ti = TimeInstall()
            ti.setup(threads, latency)
            with timeme(f"{threads} "):
                ti.time_explicit_install(threads, latency, download_only=True)


RUST_CONDA = (
    # from conda-package-streaming rust-extension branch
    # winds up being similar in speed to our Python implementation
    os.path.expanduser(
        "~/prog/conda-package-streaming/rust-conda/target/release/rust-conda"
    )
)


def conda_extract_rust(threads):
    from urllib.parse import urlparse

    from .test_server import base

    with tempfile.TemporaryDirectory() as dest:
        print(f"extract {len(SPECS)} conda's to {dest}")
        with timeme("rust extract"), ThreadPoolExecutor(threads) as pool:
            for spec in SPECS:
                if spec == "@EXPLICIT":
                    continue
                conda = urlparse(spec).path.rsplit("/")[-1]
                conda_path = base / conda
                assert conda_path.exists(), conda_path
                cmd = [RUST_CONDA, str(conda_path)]
                pool.submit(
                    partial(
                        subprocess.check_call, cmd, cwd=dest, stdout=subprocess.DEVNULL
                    )
                )


def conda_extract_streaming(threads):
    from urllib.parse import urlparse

    from .test_server import base

    with tempfile.TemporaryDirectory() as dest:
        print(f"extract {len(SPECS)} conda's to {dest}")
        with timeme("python extract"), ThreadPoolExecutor(threads) as pool:
            for spec in SPECS:
                if spec == "@EXPLICIT":
                    continue
                conda = urlparse(spec).path.rsplit("/")[-1]
                conda_path = base / conda
                assert conda_path.exists(), conda_path
                conda_dest = pathlib.Path(dest, pathlib.Path(conda).stem)
                # could use with fileobj: to avoid re-opening
                # may not support avoiding re-parse of zip?
                pool.submit(
                    partial(
                        conda_package_streaming.extract.extract, conda_path, conda_dest
                    )
                )
            # should automatically join


def main():
    logging.basicConfig()
    log.setLevel(logging.INFO)
    conda.core.package_cache_data.log.setLevel(logging.DEBUG)
    run()


if __name__ == "__main__":
    for threads in (1, 3, 7):
        print(f"Threads: {threads}")
        conda_extract_rust(threads)
        conda_extract_streaming(threads)
        print()
