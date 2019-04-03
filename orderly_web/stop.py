import docker

from orderly_web.docker_helpers import *


def stop(cfg, kill=False, network=False, volumes=False):
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
