import docker

from orderly_web.config import fetch_config
from orderly_web.docker_helpers import docker_client


def add_users(path, emails):
    args = ["add-users"] + emails
    run(path, args)


def add_groups(path, names):
    args = ["add-groups"] + names
    run(path, args)


def add_members(path, name, emails):
    args = ["add-members", name] + emails
    run(path, args)


def grant(path, name, permissions):
    args = ["grant", name] + permissions
    run(path, args)


def run(path, args):
    cfg = fetch_config(path)
    image = str(cfg.images["user-cli"])
    client = docker_client()
    mounts = [docker.types.Mount("/orderly", cfg.volumes["orderly"])]
    return client.containers.run(image, args, mounts=mounts, auto_remove=True)
