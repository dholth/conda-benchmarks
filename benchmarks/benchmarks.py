# Write the benchmarking functions here.
# See "Writing benchmarks" in the asv docs for more information.

import pathlib

from conda_package_handling.api import extract
from conda_package_streaming import package_streaming


class TimeSuite:
    """
    An example benchmark that times the performance of various kinds
    of iterating over dictionaries in Python.
    """

    def setup(self):
        self.d = {}
        for x in range(500):
            self.d[x] = None

    def time_keys(self):
        for key in self.d.keys():
            pass

    def time_values(self):
        for value in self.d.values():
            pass

    def time_range(self):
        d = self.d
        for key in range(500):
            x = d[key]


class TimeCondaPackageHandling:
    def setup(self):
        self.condas = list(
            pathlib.Path("~/miniconda3/pkgs").expanduser().glob("*.conda")
        )

    def time_cph(self):
        """
        Extract a bunch of .conda with conda-package-handling
        """
        base = pathlib.Path("/tmp/condas-cph")
        base.mkdir(exist_ok=True)
        for conda in self.condas:
            stem = conda.stem
            dest_dir = base / stem
            dest_dir.mkdir(exist_ok=True)
            extract(str(conda), dest_dir)

    def time_cps(self):
        """
        Extract a bunch of .conda with conda-package-streaming
        """
        base = pathlib.Path("/tmp/condas-cps")
        base.mkdir(exist_ok=True)
        for conda in self.condas:
            stem = conda.stem
            dest_dir = base / stem
            dest_dir.mkdir(exist_ok=True)
            with conda.open(mode="rb") as fp:
                for tar, member in package_streaming.stream_conda_component(
                    str(conda), fp, component="info"
                ):
                    tar.extractall(dest_dir)
                    break
                for tar, member in package_streaming.stream_conda_component(
                    str(conda), fp, component="pkg"
                ):
                    tar.extractall(dest_dir)
                    break


class MemSuite:
    def mem_list(self):
        return [0] * 256
