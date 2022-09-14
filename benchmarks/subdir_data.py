"""
Time SubdirData (parses repodata.json) operations.
"""

import conda.exports
from conda.core.subdir_data import (
    SubdirData,
)
from conda.models.channel import Channel

from .test_server import base

REPODATA_FILENAME = base / "osx-64" / "repodata.json"


class TimeSubdirData:
    def setup(self):
        if not REPODATA_FILENAME.exists():
            REPODATA_FILENAME.parent.mkdir(exist_ok=True)
            # fake out
            (base / "noarch").mkdir(exist_ok=True)
            (base /  "noarch" / "repodata.json").write_text("{}")
            (base /  "noarch" / "repodata.json.bz2").write_text("")
            # do we have a frozen large-ish repodata.json or can we fake one?
            conda.exports.download(
                "https://repo.anaconda.com/pkgs/main/osx-64/repodata.json",
                REPODATA_FILENAME,
            )

    def time_subdir_data(self):
        channel = Channel(f"file://{base}", platform="osx-64")
        SubdirData.clear_cached_local_channel_data()

        sd_a = SubdirData(channel)
        assert sd_a.query_all("zlib =1.2.11")

if __name__ == "__main__":
    TimeSubdirData().time_subdir_data()
