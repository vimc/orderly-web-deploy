import docker

from orderly_web.config import fetch_config
from orderly_web.docker_helpers import docker_client


def add_users(path, emails):
    args = ["add-users"] + emails
    return run(path, args)


def add_groups(path, names):
    args = ["add-groups"] + names
    return run(path, args)


def add_members(path, name, emails):
    args = ["add-members", name] + emails
    return run(path, args)


def grant(path, name, permissions):
    args = ["grant", name] + permissions
    return run(path, args)


def run(path, args):
    cfg = fetch_config(path)
    image = str(cfg.images["admin"])
    with docker_client() as cl:
        mounts = [docker.types.Mount("/orderly", cfg.volumes["orderly"])]
        result = return_logs_and_remove(cl, image, args, mounts)
        print(result)
        return result


def return_logs_and_remove(client, image, args=None, mounts=None):
    try:
        container = client.containers.run(image, args, mounts=mounts,
                                          detach=True)
        container.wait()
        return container.logs().decode("UTF-8")
    finally:
        container.remove()
