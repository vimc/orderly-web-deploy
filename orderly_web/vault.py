import hvac
import os
import re


def resolve_secret(value, client):
    re_vault = re.compile("^VAULT:([^:]+):([^:]+)$")
    if not value.startswith("VAULT:"):
        return False, value
    m = re_vault.match(value)
    if not m:
        raise Exception("Invalid vault accessor '{}'".format(value))
    path, key = m.groups()
    data = client.read(path)
    if not data:
        raise Exception("Did not find secret at '{}'".format(path))
    if not data["data"]:
        raise Exception("Did not find key '{}' at secret path '{}'".format(
            key, path))
    return True, data["data"][key]


class vault_config:
    def __init__(self, url, auth_method, auth_args):
        self.url = url
        self.auth_method = auth_method
        self.auth_args = auth_args

    def client(self):
        if not self.url:
            return vault_not_enabled()
        # NOTE: we might actually try and pick up VAULT_TOKEN from the
        # environment, but can't let that value override any value
        # passed here.
        drop_envvar("VAULT_ADDR")
        drop_envvar("VAULT_TOKEN")
        if self.auth_method == "token":
            cl = hvac.Client(url=self.url, token=self.auth_args["token"])
        else:
            cl = hvac.Client(url=self.url)
            getattr(cl)(**self.auth_args)
        return cl


class vault_not_enabled:
    def __getattr__(self, name):
        raise Exception("Vault access is not enabled")


def drop_envvar(name):
    if name in os.environ:
        del os.environ[name]
