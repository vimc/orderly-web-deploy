import docker

from orderly_web.config import fetch_config, build_config
from orderly_web.constellation import orderly_constellation
from orderly_web.errors import OrderlyWebConfigError


def status(path):
    try:
        cfg = fetch_config(path)
    except docker.errors.NotFound as e:
        cfg = build_config(path)
    if cfg:
        try:
            obj = orderly_constellation(cfg)
            obj.status()
        except AttributeError as e:
            msg = ("Unable to manage constellation from existing config."
                   " The format of the config may have changed. You should"
                   " force a stop and restart.")
            raise OrderlyWebConfigError(msg) from e
    else:
        print("OrderlyWeb not running from '{}'".format(path))
