import docker

from orderly_web.config import fetch_config
from orderly_web.docker_helpers import docker_client


def add_user(email):
    args = ["add-user", email]
    run(args)


def add_group(name):
    args = ["add-group", name]
    run(args)


def add_members(name, emails):
    args = ["add-group", name, emails]
    run(args)


def grant(name, permissions):
    args = ["grant", name, permissions]
    run(args)


def run(args):
    cfg = fetch_config("")
    image = str(cfg.images["user-cli"])
    client = docker_client()
    mounts = [docker.types.Mount("/orderly", cfg.volumes["orderly"])]
    client.containers.run(image, args, mounts=mounts, auto_remove=True)
