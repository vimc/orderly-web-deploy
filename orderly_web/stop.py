import docker

from orderly_web.config import fetch_config, build_config
from orderly_web.constellation import orderly_constellation
from orderly_web.errors import OrderlyWebConfigError


def stop(path, kill=False, network=False, volumes=False, force=False,
         extra=None, options=None):
    try:
        cfg = fetch_config(path)
    except docker.errors.NotFound as e:
        if force:
            print("Unable to fetch config from orderly-web, forcing stop.")
            cfg = build_config(path, extra, options)
        else:
            msg = ("Unable to fetch config from orderly-web. To force stop, "
                   "provide --force option and any configuration options in "
                   "--extra and --options.")
            raise OrderlyWebConfigError(msg) from e

    if cfg:
        try:
            obj = orderly_constellation(cfg)
        except AttributeError as e:
            if force:
                print("Unable to manage constellation from existing config, "
                      "forcing stop.")
                cfg = build_config(path, extra, options)
                obj = orderly_constellation(cfg)
            else:
                msg = ("Unable to manage constellation from existing config. "
                       "To force stop, provide --force option and any "
                       "configuration options in --extra and --options.")
                raise OrderlyWebConfigError(msg) from e
        obj.stop(kill, remove_network=network, remove_volumes=volumes)
    else:
        print("OrderlyWeb not running from '{}'".format(path))
