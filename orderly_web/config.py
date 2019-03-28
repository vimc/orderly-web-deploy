import docker
import yaml

from orderly_web.docker_helpers import docker_client


def read_config(path):
    path_yml = "{}/orderly-web.yml".format(path)
    with open(path_yml, "r") as f:
        dat = yaml.load(f, Loader=yaml.SafeLoader)
    return OrderlyWebConfig(dat)


class OrderlyWebConfig:

    def __init__(self, dat):
        self.data = dat
        self.network = config_string(dat, ["network"])
        self.volumes = {
            "orderly": config_string(dat, ["volumes", "orderly"])
        }

        self.container_prefix = config_string(dat, ["container_prefix"])
        self.containers = {
            "orderly": "{}_orderly".format(self.container_prefix),
            "web": "{}_web".format(self.container_prefix)
        }

        self.images = {
            "orderly": config_image_reference(dat, ["orderly", "image"]),
            "web": config_image_reference(dat, ["web", "image"]),
            "migrate": config_image_reference(dat, ["web", "image"], "migrate")
        }

        self.web_dev_mode = config_boolean(dat, ["web", "dev_mode"], True)
        self.web_port = config_integer(dat, ["web", "port"])
        self.web_name = config_string(dat, ["web", "name"])
        self.web_email = config_string(dat, ["web", "email"])

        self.web_auth_montagu = config_boolean(
            dat, ["web", "auth", "montagu"])
        self.web_auth_fine_grained = config_boolean(
            dat, ["web", "auth", "fine_grained"])
        self.web_auth_github_org = config_string(
            dat, ["web", "auth", "github_org"], True)
        self.web_auth_github_team = config_string(
            dat, ["web", "auth", "github_team"], True)

    def get_container(self, name):
        with docker_client() as cl:
            return cl.containers.get(self.containers[name])


class DockerImageReference:

    def __init__(self, repo, name, tag):
        self.repo = repo
        self.name = name
        self.tag = tag

    def __str__(self):
        return "{}/{}:{}".format(self.repo, self.name, self.tag)


# Utility function for centralising control over pulling information
# out of the configuration.
def config_value(data, path, data_type, is_optional):
    if type(path) is str:
        path = [path]
    for i, p in enumerate(path):
        try:
            data = data[p]
        except KeyError as e:
            if is_optional:
                return None
            e.args = (":".join(path[:(i + 1)]), )
            raise e

    expected = {"string": str,
                "integer": int,
                "boolean": bool}
    if type(data) is not expected[data_type]:
        raise ValueError("Expected {} for {}".format(
            data_type, ":".join(path)))
    return data


def config_string(data, path, is_optional=False):
    return config_value(data, path, "string", is_optional)


def config_integer(data, path, is_optional=False):
    return config_value(data, path, "integer", is_optional)


def config_boolean(data, path, is_optional=False):
    return config_value(data, path, "boolean", is_optional)


def config_image_reference(dat, path, name="name"):
    if type(path) is str:
        path = [path]
    repo = config_string(dat, path + ["repo"])
    name = config_string(dat, path + [name])
    tag = config_string(dat, path + ["tag"])
    return DockerImageReference(repo, name, tag)
