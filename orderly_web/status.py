import docker

from orderly_web.config import fetch_config, build_config
from orderly_web.constellation import orderly_constellation


def status(path):
    try:
        cfg = fetch_config(path)
    except docker.errors.NotFound as e:
        cfg = build_config(path)
    if cfg:
        obj = orderly_constellation(cfg)
        obj.status()
    else:
        print("OrderlyWeb not running from '{}'".format(path))
