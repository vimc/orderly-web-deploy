import docker

from orderly_web.config import fetch_config, build_config
from orderly_web.constellation import orderly_constellation


def status(path):
    cfg = build_config(path)
    obj = orderly_constellation(cfg)
    obj.status()
