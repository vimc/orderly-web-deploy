import docker

from orderly_web.config import fetch_config
from orderly_web.docker_helpers import docker_client


def add_users(emails):
    args = ["add-users"] + emails
    run(args)


def add_groups(names):
    args = ["add-groups"] + names
    run(args)


def add_members(name, emails):
    args = ["add-members", name] + emails
    run(args)


def grant(name, permissions):
    args = ["grant", name] + permissions
    run(args)


def run(args):
    cfg = fetch_config("")
    image = str(cfg.images["user-cli"])
    client = docker_client()
    mounts = [docker.types.Mount("/orderly", cfg.volumes["orderly"])]
    return client.containers.run(image, args, mounts=mounts, auto_remove=True)
