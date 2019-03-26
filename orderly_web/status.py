import docker

from orderly_web.docker_helpers import docker_client


def status(cfg):
    return OrderlyWebStatus(cfg)


class OrderlyWebStatus:

    def __init__(self, cfg):
        self.cfg = cfg
        self.reload()

    def __str__(self):
        st_c = dict_map(self.containers, lambda k, v: "  {}: {} ({})".format(
            k, v["status"], v["name"]))
        st_v = dict_map(self.volumes, lambda k, v: "  {}: {} ({})".format(
            k, v["status"], v["name"]))
        st_n = "Network: {} ({})".format(
            self.network["status"], self.network["name"])
        ret = ["OrderlyWeb: {}".format(self.cfg.web_name)]
        ret += ["Containers:"] + st_c
        ret += ["Volumes:"] + st_v
        ret += [st_n]
        return "\n".join(ret)

    def __repr__(self):
        return self.__str__()

    def reload(self):
        with docker_client() as client:
            self.containers = {k: container_status(client, v)
                               for k, v in self.cfg.containers.items()}
            self.volumes = {k: volume_status(client, v)
                            for k, v in self.cfg.volumes.items()}
            self.network = network_status(client, self.cfg.network)


def container_status(client, name):
    try:
        status = client.containers.get(name).status
    except docker.errors.NotFound:
        status = "missing"
    return {"name": name, "status": status}


def volume_status(client, name):
    try:
        client.volumes.get(name)
        status = "created"
    except docker.errors.NotFound:
        status = "missing"
    return {"name": name, "status": status}


def network_status(client, name):
    try:
        client.networks.get(name)
        status = "up"
    except docker.errors.NotFound:
        status = "down"
    return {"name": name, "status": status}


def dict_map(x, f):
    return [f(k, x[k]) for k in sorted(x.keys())]
