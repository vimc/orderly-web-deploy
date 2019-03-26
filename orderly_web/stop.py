import docker

from orderly_web.docker_helpers import *


def stop(cfg, network=False, volumes=False):
    client = docker.client.from_env()
    kill_and_remove_container(client, cfg.containers["web"])
    kill_and_remove_container(client, cfg.containers["orderly"])
    if network:
        remove_network(client, cfg.network)
    if volumes:
        for v in cfg.volumes.values():
            remove_volume(client, v)
