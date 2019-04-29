import docker

from orderly_web.config import read_config
from orderly_web.docker_helpers import *


def stop(path, kill=False, network=False, volumes=False):
    cfg_base = read_config(path)
    cfg = cfg_base.fetch(False)

    if cfg:
        print("Stopping OrderlyWeb from '{}'".format(path))
        with docker_client() as client:
            if "proxy" in cfg.containers:
                stop_and_remove_container(client, cfg.containers["proxy"], kill)
            stop_and_remove_container(client, cfg.containers["web"], kill)
            stop_and_remove_container(client, cfg.containers["orderly"], kill)
            if network:
                remove_network(client, cfg.network)
            if volumes:
                for v in cfg.volumes.values():
                    remove_volume(client, v)
    else:
        print("OrderlyWeb not running from '{}'".format(path))
