import docker

from orderly_web.config import read_config
from orderly_web.docker_helpers import docker_client


def status(path):
    return OrderlyWebStatus(path)


class OrderlyWebStatus:
    def __init__(self, path):
        self.path = path
        self.reload()

    def __str__(self):
        if not self.is_running:
            return "<not running>"
        st_c = dict_map(self.containers, format_container)
        st_v = dict_map(self.volumes, format_volume)
        st_n = "Network: {}".format(self.network)
        ret = ["OrderlyWeb status:"]
        if st_c:
            ret += ["Containers:"] + st_c
        if st_v:
            ret += ["Volumes:"] + st_v
        ret += [st_n]
        return "\n".join(ret)

    def __repr__(self):
        return self.__str__()

    def reload(self):
        cfg_base = read_config(self.path)
        cfg_running = cfg_base.fetch()

        self.is_running = bool(cfg_running)
        with docker_client() as client:
            self.containers = {k: container_status(client, v)
                               for k, v in cfg_base.containers.items()}
            if cfg_running:
                self.volumes = cfg_running.volumes
                self.network = cfg_running.network
            else:
                self.volumes = {}
                self.network = None


def format_container(role, status):
    return "  {}: {} ({})".format(role, status["status"], status["name"])


def format_volume(role, name):
    return "  {}: {}".format(role, name)


def container_status(client, name):
    try:
        status = client.containers.get(name).status
    except docker.errors.NotFound:
        status = "missing"
    return {"name": name, "status": status}


def dict_map(x, f):
    return [f(k, x[k]) for k in sorted(x.keys())]
