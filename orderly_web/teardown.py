import docker

from orderly_web.docker_helpers import *


def teardown(cfg, network=False, volumes=False):
    client = docker.client.from_env()
    kill_and_remove_container(client, cfg.container_name_web)
    kill_and_remove_container(client, cfg.container_name_orderly)
    if network:
        remove_network(client, cfg.network)
    if volumes:
        for v in cfg.volumes.values():
            remove_volume(client, v)
