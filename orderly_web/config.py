import base64
import docker
import pickle
import yaml

from orderly_web.docker_helpers import docker_client, string_from_container, \
    string_into_container
import orderly_web.vault as vault

# We will store a configuration into this (container, path) pair; it
# does not really matter where it is but it is ideal if it is not on a
# part of the filesystem that is persisted (i.e., not a volume)
# because it might contain secrets.
PATH_CONFIG = {"container": "orderly", "path": "/orderly-web-config"}


def read_config(path, extra=None, options=None):
    dat = read_config_data(path, extra, options)
    return OrderlyWebConfig(dat)


def fetch_config(path, error=False):
    return read_config(path).fetch(error)


def read_config_data(path, extra=None, options=None):
    dat = read_yaml("{}/orderly-web.yml".format(path))
    if extra:
        dat_extra = read_yaml("{}/{}.yml".format(path, extra))
        if "container_prefix" in dat_extra:
            raise Exception("'container_prefix' may not be modified")
        dat = combine(dat, dat_extra)
    if options:
        dat = combine(dat, options)
        if "container_prefix" in options:
            raise Exception("'container_prefix' may not be modified")
    return dat


def read_yaml(filename):
    with open(filename, "r") as f:
        dat = yaml.load(f, Loader=yaml.SafeLoader)
    return dat


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

    def save(self):
        orderly = self.get_container("orderly")
        txt = base64.b64encode(pickle.dumps(self)).decode("utf8")
        container = self.get_container(PATH_CONFIG["container"])
        path = PATH_CONFIG["path"]
        string_into_container(txt, container, path)

    def fetch(self, error=True):
        try:
            container = self.get_container(PATH_CONFIG["container"])
        except docker.errors.NotFound:
            if error:
                raise
            return None
        path = PATH_CONFIG["path"]
        txt = string_from_container(container, path)
        return pickle.loads(base64.b64decode(txt))

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


def combine(a, b):
    """Combine exactly two dictionaries recursively"""
    for k, v in b.items():
        if k in a and type(a[k]) is dict:
            combine(a[k], v)
        else:
            a[k] = v
    return a


def string_to_dict(key, value):
    """Convert a configuration key a.b.c with value x to a dictionary
{"a": {"b": "c": x}}"""
    # Won't deal with dots embedded within quotes but that's ok as
    # that should not be allowed generally.
    for k in reversed(key.split(".")):
        value = {k: value}
    return value
