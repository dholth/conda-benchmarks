"""
Flask-based conda repository server for testing.

Change contents to simulate an updating repository.
"""

from pathlib import Path
from threading import Thread

import time
import flask

from werkzeug.serving import make_server

app = flask.Flask(__name__)

base = Path(__file__).parents[1] / "env" / "conda-asyncio"

# flask.send_from_directory(directory, path, **kwargs)
# Send a file from within a directory using send_file().
@app.route("/<subdir>/<path:name>")
def download_file(subdir, name):
    # conditional=True is the default
    return flask.send_from_directory(base, name)

def run_on_random_port():
    server = make_server(host="127.0.0.1", port=0, app=app, threaded=True)
    Thread(target=server.serve_forever, daemon=True).start()
    return server

if __name__ == "__main__":
    print(run_on_random_port())
    time.sleep(60)
