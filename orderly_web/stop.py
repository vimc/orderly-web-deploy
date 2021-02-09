import docker

from orderly_web.config import fetch_config, build_config
from orderly_web.docker_helpers import *
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
        print("Stopping OrderlyWeb from '{}'".format(path))
        with docker_client() as client:
            if "proxy" in cfg.containers:
                stop_and_remove_container(client, cfg.containers["proxy"],
                                          kill)
            stop_and_remove_container(client, cfg.containers["web"], kill)
            workers = list_containers(client,
                                      cfg.container_groups["orderly_worker"]
                                      ["name"])
            for worker in workers:
                stop_and_remove_container(client, worker.name, kill)
            stop_and_remove_container(client, cfg.containers["orderly"], kill)
            stop_and_remove_container(client, cfg.containers["redis"], kill)
            if network:
                remove_network(client, cfg.network)
            if volumes:
                for v in cfg.volumes.values():
                    remove_volume(client, v)
    else:
        print("OrderlyWeb not running from '{}'".format(path))
