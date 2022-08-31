"""
https://github.com/conda/conda/issues/11608
"""

import asyncio
import hashlib
import logging
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List
from urllib.parse import urlparse

import aiofiles
import aiohttp
import yaml
from conda_package_handling import api

from . import test_server
import conda.exports

log = logging.getLogger(__name__)

PLATFORM = "osx-64"  # adjust based on conda-lock.yml

cheap = yaml.load(
    (Path(__file__).parent / "../conda-lock.yml").open(), Loader=yaml.SafeLoader
)


def extract(sha256: str, file: str, target: str):
    hasher = hashlib.new("sha256")
    with open(file, "rb") as fh:
        for chunk in iter(partial(fh.read, 8192), b""):
            hasher.update(chunk)
    assert hasher.hexdigest() == sha256
    print("Extracting", file, target)
    api.extract(file, target)


async def main(packages: List[Dict], root: Path):
    async with aiohttp.ClientSession() as session:
        tasks = []
        urls = []
        for package in packages:
            if package["platform"] == PLATFORM and package["manager"] == "conda":
                url = package["url"]
                parsed = urlparse(url)
                pth = Path(parsed.path)
                pth.name
                tasks.append(
                    download_url(
                        sha256=package["hash"]["sha256"],
                        session=session,
                        fp=root / pth.name,
                        url=package["url"],
                    )
                )
                urls.append(url)
        await asyncio.gather(*tasks)
        async with aiofiles.open(root / Path("urls.txt").expanduser(), mode="w") as f:
            for url in urls:
                await f.write(url + "\n")
        async with aiofiles.open(root / Path("urls").expanduser(), mode="w") as f:
            await f.write("\n")


async def download_url(session: aiohttp.ClientSession, sha256: str, fp: Path, url: str):
    log.info("Download %s", url)
    async with session.get(url) as resp:
        async with aiofiles.open(fp, mode="wb") as f:
            async for chunk in resp.content.iter_chunked(10000):
                await f.write(chunk)
    log.info("Finish %s", url)

    loop = asyncio.get_running_loop()
    target_dir = (
        str(fp).removesuffix(".tar.bz2").removesuffix(".tar").removesuffix(".conda")
    )
    # await loop.run_in_executor(p, extract, sha256, str(fp), target_dir)


class TimeDownloadPackages:
    def setup(self):
        self.tempdir = TemporaryDirectory("aiohttp")
        self.temppath = Path(self.tempdir.name)
        log.info("Download to %s", self.tempdir)
        self.server = test_server.run_on_random_port()

    def teardown(self):
        self.tempdir.cleanup()

    def setup_cache(self):
        """
        Called once per session.
        """
        test_server.base.mkdir(parents=True, exist_ok=True)
        for package in cheap["package"]:
            name = package["url"].rpartition("/")[-1]
            if not (test_server.base / name).exists():
                conda.exports.download(package["url"], test_server.base / name)

    def fixup_urls(self):
        """
        Retarget urls against our local test server.
        """
        port = self.server.port
        packages = []
        for package in cheap["package"]:
            name = package["url"].rsplit("/", 1)[-1]
            packages.append({**package, "url":f"http://127.0.0.1:{port}/osx-64/{name}"})
        return packages

    def time_download_aiohttp(self):
        asyncio.run(main(self.fixup_urls(), self.temppath))

    def time_download_serial(self):
        # does teardown/setup not run for each function in this class
        target_base = self.temppath / 's'
        target_base.mkdir()
        for package in self.fixup_urls():
            name = package['url'].rsplit('/', 1)[-1]
            target = target_base / name
            assert not target.exists()
            conda.exports.download(package["url"], target)

if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    t = TimeDownloadPackages()
    t.setup()
    t.time_download_aiohttp()
