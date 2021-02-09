import docker

from orderly_web.config import read_config
from orderly_web.docker_helpers import docker_client, list_containers


def print_status(path):
    print(status(path))


def status(path):
    return OrderlyWebStatus(path)


class OrderlyWebStatus:
    def __init__(self, path):
        self.path = path
        self.reload()

    def __str__(self):
        if self.cannot_read_status:
            return "Cannot read status from orderly-web because it has not " \
                "started successfully or is in an error state."
        if not self.is_running:
            return "<not running>"
        st_c = dict_map(self.containers, format_container)
        st_cg = dict_map(self.container_groups, format_container_group)
        st_v = dict_map(self.volumes, format_volume)
        st_n = "Network: {}".format(self.network)
        ret = ["OrderlyWeb status:"]
        if st_c:
            ret += ["Containers:"] + st_c + st_cg
        if st_v:
            ret += ["Volumes:"] + st_v
        ret += [st_n]
        return "\n".join(ret)

    def __repr__(self):
        return self.__str__()

    def reload(self):
        cfg_base = read_config(self.path)

        cfg_running = False

        try:
            cfg_running = cfg_base.fetch()
            self.cannot_read_status = False
        except docker.errors.NotFound:
            self.cannot_read_status = True

        self.is_running = bool(cfg_running)
        with docker_client() as client:
            self.containers = {
                k: container_status(client, v)
                for k, v in cfg_base.containers.items()
            }
            self.container_groups = {
                k: container_group_status(client, v)
                for k, v in cfg_base.container_groups.items()
            }
            if cfg_running:
                self.volumes = cfg_running.volumes
                self.network = cfg_running.network
            else:
                self.volumes = {}
                self.network = None


def format_container(role, status):
    return "  {}: {} ({})".format(role, status["status"], status["name"])


def format_container_group(role, status):
    group_status = ["  {} ({}/{}):".format(role, status["count"],
                                           status["scale"])]
    for container in status["status"]:
        group_status.append("    - {} ({})".format(container["status"],
                                                   container["name"]))
    return "\n".join(group_status)


def format_volume(role, name):
    return "  {}: {}".format(role, name)


def container_status(client, name):
    try:
        status = client.containers.get(name).status
    except docker.errors.NotFound:
        status = "missing"
    return {"name": name, "status": status}


def container_group_status(client, group):
    containers = list_containers(client, group["name"])
    status = {
        "scale": group["scale"],
        "count": len(containers),
        "status": []
    }
    for container in containers:
        status["status"].append({"name": container.name,
                                 "status": container.status})
    return status


def dict_map(x, f):
    return [f(k, x[k]) for k in sorted(x.keys())]
