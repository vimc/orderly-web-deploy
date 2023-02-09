import docker

from orderly_web.config import fetch_config, build_config
from orderly_web.constellation import orderly_constellation
from orderly_web.errors import OrderlyWebConfigError


def status(path, force=False):
    try:
        cfg = fetch_config(path)
    except docker.errors.NotFound as e:
        cfg = build_config(path)
    if cfg:
        try:
            obj = orderly_constellation(cfg)
        except AttributeError as e:
            if force:
                print("Unable to manage constellation from existing config, building new config.")
                cfg = build_config(path)
                obj = orderly_constellation(cfg)
            else:
                msg = ("Unable to manage constellation from existing config, "
                       "provide --force option to build new config.")
                raise OrderlyWebConfigError(msg) from e
        obj.status()
    else:
        print("OrderlyWeb not running from '{}'".format(path))
