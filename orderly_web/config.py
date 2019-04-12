import docker
import yaml

from orderly_web.docker_helpers import docker_client
import orderly_web.vault as vault


def read_config(path):
    path_yml = "{}/orderly-web.yml".format(path)
    with open(path_yml, "r") as f:
        dat = yaml.load(f, Loader=yaml.SafeLoader)
    return OrderlyWebConfig(dat)


class OrderlyWebConfig:

    def __init__(self, dat):
        self.data = dat
        self.vault = config_vault(dat, ["vault"])
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

        self.orderly_env = config_dict(dat, ["orderly", "env"], True)

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

        if "proxy" in dat and dat["proxy"]:
            self.proxy_enabled = config_boolean(
                dat, ["proxy", "enabled"])
            self.proxy_hostname = config_string(
                dat, ["proxy", "hostname"])
            self.proxy_port_http = config_integer(
                dat, ["proxy", "port_http"])
            self.proxy_port_https = config_integer(
                dat, ["proxy", "port_https"])
            ssl = config_dict(dat, ["proxy", "ssl"], True)
            self.proxy_ssl_self_signed = ssl is None
            if not self.proxy_ssl_self_signed:
                self.proxy_ssl_certificate = config_string(
                    dat, ["proxy", "ssl", "certificate"], True)
                self.proxy_ssl_key = config_string(
                    dat, ["proxy", "ssl", "key"], True)
            self.images["proxy"] = config_image_reference(
                dat, ["proxy", "image"])
            self.volumes["proxy_logs"] = config_string(
                dat, ["volumes", "proxy_logs"])
            self.containers["proxy"] = "{}_proxy".format(self.container_prefix)
        else:
            self.proxy_enabled = False

    def get_container(self, name):
        with docker_client() as cl:
            return cl.containers.get(self.containers[name])

    def resolve_secrets(self):
        vault_client = self.vault.client()
        vault.resolve_secrets(self, vault_client)
        vault.resolve_secrets(self.orderly_env, vault_client)


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
            if data is None:
                raise KeyError()
        except KeyError as e:
            if is_optional:
                return None
            e.args = (":".join(path[:(i + 1)]), )
            raise e

    expected = {"string": str,
                "integer": int,
                "boolean": bool,
                "dict": dict}
    if type(data) is not expected[data_type]:
        raise ValueError("Expected {} for {}".format(
            data_type, ":".join(path)))
    return data


# TODO: once we have support for easily overriding parts of
# configuration, this can be made better with respect to optional
# values (e.g., if url is present other keys are required).
def config_vault(data, path):
    url = config_string(data, path + ["addr"], True)
    auth_method = config_string(data, path + ["auth", "method"], True)
    auth_args = config_dict(data, path + ["auth", "args"], True)
    return vault.vault_config(url, auth_method, auth_args)


def config_string(data, path, is_optional=False):
    return config_value(data, path, "string", is_optional)


def config_integer(data, path, is_optional=False):
    return config_value(data, path, "integer", is_optional)


def config_boolean(data, path, is_optional=False):
    return config_value(data, path, "boolean", is_optional)


def config_dict(data, path, is_optional=False):
    return config_value(data, path, "dict", is_optional)


def config_image_reference(dat, path, name="name"):
    if type(path) is str:
        path = [path]
    repo = config_string(dat, path + ["repo"])
    name = config_string(dat, path + [name])
    tag = config_string(dat, path + ["tag"])
    return DockerImageReference(repo, name, tag)


def combine(*args):
    """Combine a number of dictionaries recursively"""
    a = args[0]
    for b in args[1:]:
        a = combine2(a, b)
    return a


def combine2(a, b):
    """Combine exactly two dictionaries recursively"""
    for k, v in b.items():
        if k in a and type(a[k]) is dict:
            combine(a[k], v)
        else:
            a[k] = v
    return a
