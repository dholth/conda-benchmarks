#!/usr/bin/env python
import benchmarks.conda_install
# this multithreaded profiler crashes when we try to use multiprocessing to
# start our test web server?
import yappi
yappi.set_clock_type("wall")
yappi.start()

ti = benchmarks.conda_install.TimeInstall()
ti.setup(10, server=False)
ti.time_download_lockfile()

