# Write the benchmarking functions here.
# See "Writing benchmarks" in the asv docs for more information.

import pathlib
from tempfile import TemporaryDirectory
import time
from tkinter.tix import MAX

from conda_package_handling.api import extract
from conda_package_streaming import package_streaming


MINIMUM_PACKAGES = 10
MAXIMUM_SECONDS = 8.0


class TrackSuite:
    def setup(self):
        self.condas = list(
            pathlib.Path("~/miniconda3/pkgs").expanduser().glob("*.conda")
        )
        if len(self.condas) < MINIMUM_PACKAGES:
            raise NotImplementedError("Not enough .conda packages in ~/miniconda3/pkgs")

        self.tarbz2 = list(
            pathlib.Path("~/miniconda3/pkgs").expanduser().glob("*.tar.bz2")
        )

    def track_streaming_versus_handling(self):
        """
        Compare conda-package-streaming time versus conda-package-handling (should be a number > 1)
        """
        attempted = len(self.condas)
        with TemporaryDirectory(
            "conda-package-streaming"
        ) as streaming, TemporaryDirectory("conda-package-handling") as handling:

            # give faster streaming the cache disadvantage
            begin = time.monotonic()
            # revise self.condas down to the number extracted in no more thanœ
            # MAXIMUM_SECONDS
            self.condas = extract_streaming(streaming, self.condas)
            end = time.monotonic()
            cps_time = end - begin

            actual = len(self.condas)
            print(f"'streaming' extracted {actual} out of {attempted} .conda's")

            begin = time.monotonic()
            self.condas = extract_handling(handling, self.condas, time_limit=cps_time * 4)
            end = time.monotonic()
            handling_time = end - begin

            actual = len(self.condas)
            print(f"'handling' extracted {actual} out of {attempted} .conda's")

            return handling_time / cps_time


    def track_streaming_versus_handling_tarbz2(self):
        """
        Compare conda-package-streaming time versus conda-package-handling (should be a number > 1)
        """
        attempted = len(self.condas)
        with TemporaryDirectory(
            "conda-package-streaming-bz2"
        ) as streaming, TemporaryDirectory("conda-package-handling-bz2") as handling:

            # give faster streaming the cache disadvantage
            begin = time.monotonic()
            # revise self.condas down to the number extracted in no more thanœ
            # MAXIMUM_SECONDS
            self.tarbz2 = extract_streaming(streaming, self.tarbz2)
            end = time.monotonic()
            cps_time = end - begin

            actual = len(self.condas)
            print(f"'streaming' extracted {actual} out of {attempted} .tar.bz2's")

            begin = time.monotonic()
            self.tarbz2 = extract_handling(handling, self.tarbz2, time_limit=cps_time * 4)
            end = time.monotonic()
            handling_time = end - begin

            actual = len(self.condas)
            print(f"'handling' extracted {actual} out of {attempted} .tar.bz2's")

            return handling_time / cps_time

def extract_handling(base, condas, time_limit=MAXIMUM_SECONDS):
    """
    Extract a bunch of .conda with conda-package-handling
    """
    limit = time.monotonic()
    extracted = []
    base = pathlib.Path(base)
    for conda in condas:
        stem = conda.stem
        dest_dir = base / stem
        dest_dir.mkdir(exist_ok=True)
        extract(str(conda), dest_dir)
        extracted.append(conda)
        if time.monotonic() - limit > time_limit:
            break

    return extracted

def extract_streaming(base, condas, time_limit=MAXIMUM_SECONDS):
    """
    Extract a bunch of .conda with conda-package-streaming
    """
    limit = time.monotonic()
    extracted = []
    base = pathlib.Path(base)
    for conda in condas:
        stem = conda.stem
        dest_dir = base / stem
        dest_dir.mkdir(exist_ok=True)
        with conda.open(mode="rb") as fp:
            for tar, _member in package_streaming.stream_conda_component(
                str(conda), fp, component="info"
            ):
                tar.extractall(dest_dir)
                break
            if conda.name.endswith(".tar.bz2"):
                break  # .tar.bz2 will be totally extracted, doesn't filter by component here
            for tar, _member in package_streaming.stream_conda_component(
                str(conda), fp, component="pkg"
            ):
                tar.extractall(dest_dir)
                break
        extracted.append(conda)
        if time.monotonic() - limit > time_limit:
            break

    return extracted
