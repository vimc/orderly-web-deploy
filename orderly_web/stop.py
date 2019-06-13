import docker

from orderly_web.config import fetch_config, build_config
from orderly_web.docker_helpers import *
from requests.exceptions import HTTPError


def stop(path, kill=False, network=False, volumes=False, force=False,
         extra=None, options=None):
    try:
        cfg = fetch_config(path)
    except HTTPError:
        print("Unable to fetch config from orderly-web.")
        if force:
            print("Forcing stop.")
            cfg = build_config(path, extra, options)
        else:
            print("To force stop, provide --force option and any "
                  "configuration options in --extra and --options.")
            return

    if cfg:
        print("Stopping OrderlyWeb from '{}'".format(path))
        with docker_client() as client:
            if "proxy" in cfg.containers:
                stop_and_remove_container(client, cfg.containers["proxy"],
                                          kill)
            stop_and_remove_container(client, cfg.containers["web"], kill)
            stop_and_remove_container(client, cfg.containers["orderly"], kill)
            if network:
                remove_network(client, cfg.network)
            if volumes:
                for v in cfg.volumes.values():
                    remove_volume(client, v)
    else:
        print("OrderlyWeb not running from '{}'".format(path))
