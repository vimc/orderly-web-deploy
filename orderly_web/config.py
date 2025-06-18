import base64
import os

import docker
import pickle

import constellation
import constellation.docker_util as docker_util
import constellation.config as config
import constellation.vault as vault

from orderly_web.docker_helpers import docker_client

# There are two types of configuration objects and three ways that
# they turn up.  These are:

# 1. A base configuration object (`OrderlyWebConfigBase`), which
#    requires a path.  This contains only the immutable bits (which is
#    the container prefix and the container names).  This object can
#    be used to create or retrieve a full configuration.  These
#    objects are created by `read_config`
#
# 2. A full configuration object (`OrderlyWebConfig`), with all
#    options set.  This can be created by:
#
#    a. The `build()` method of the `OrderlyWebConfigBase` object, by
#       adding additional options into the base configuration.  This
#       is used when starting an OrderlyWeb constellation.  This is
#       also do-able in one step with `build_config`
#
#    b. The `fetch()` method of the `OrderlyWebConfigBase` object,
#       which retrieves a pickled configuration object from the
#       running orderly container (which stores all the options as
#       used when starting).  Also doable with `fetch_config`
#
# The idea here is that interacting with an existing set of containers
# (currently limited to status and stop, but eventually we will
# support at least upgrade too) we should not have to remember any
# additional arguments that were passed to create the container, but
# at the same time we want the startup to be configurable without
# having to edit the master configuration file.
#
# We will store a configuration into this (container, path) pair; it
# does not really matter where it is but it is ideal if it is not on a
# part of the filesystem that is persisted (i.e., not a volume)
# because it might contain secrets.
PATH_CONFIG = {"container": "orderly", "path": "/orderly-web-config"}


def read_config(path):
    return OrderlyWebConfigBase(path)


def build_config(path, extra=None, options=None):
    return read_config(path).build(extra, options)


def fetch_config(path):
    return read_config(path).fetch()


class OrderlyWebConfigBase:
    def __init__(self, path):
        self.path = path
        self.data = config.read_yaml("{}/orderly-web.yml".format(path))
        self.container_prefix = config.config_string(
            self.data, ["container_prefix"])

        self.containers = {
            # This silly name (redis_ow) is to avoid potential
            # collisions when running side-by-side with packit
            "redis": "redis-ow",
            "orderly": "orderly",
            "orderly-worker": "orderly-worker",
            "web": "web"
        }

        self.workers = config.config_integer(
            self.data, ["orderly", "workers"], is_optional=True, default=1)

    def build(self, extra=None, options=None):
        data = config.config_build(self.path, self.data, extra, options)
        return OrderlyWebConfig(self.path, data)

    def fetch(self):
        try:
            with docker_client() as cl:
                name = self.containers[PATH_CONFIG["container"]]
                container = cl.containers.get(
                    "{}-{}".format(self.container_prefix, name))
        except docker.errors.NotFound:
            return None
        path = PATH_CONFIG["path"]
        txt = docker_util.string_from_container(container, path)
        cfg = pickle.loads(base64.b64decode(txt))
        # We have to set the path because the relative path (or even
        # absolute path) might be different between different users of
        # the same configuration, as the docker container is a global
        # resource.
        cfg.path = self.path
        return cfg


class OrderlyWebConfig:
    def __init__(self, path, dat):
        self.path = path
        self.data = dat
        self.vault = config.config_vault(dat, ["vault"])
        self.network = config.config_string(dat, ["network"])
        self.volumes = {
            "redis": config.config_string(dat, ["volumes", "redis"]),
            "orderly": config.config_string(dat, ["volumes", "orderly"])
        }

        self.container_prefix = config.config_string(dat, ["container_prefix"])

        self.workers = config.config_integer(
            self.data, ["orderly", "workers"], is_optional=True, default=1)

        # 1. Redis
        self.redis_name = config.config_string(
            dat, ["redis", "image", "name"])
        self.redis_tag = config.config_string(dat, ["redis", "image", "tag"])
        self.redis_ref = constellation.ImageReference(
            "library", self.redis_name, self.redis_tag)

        # 2. Orderly
        self.orderly_repo = config.config_string(
            dat, ["orderly", "image", "repo"])
        self.orderly_name = config.config_string(
            dat, ["orderly", "image", "name"])
        self.orderly_tag = config.config_string(
            dat, ["orderly", "image", "tag"])
        self.orderly_ref = constellation.ImageReference(
            self.orderly_repo, self.orderly_name, self.orderly_tag)

        # 3. Orderly worker
        self.orderly_worker_name = config.config_string(
            dat, ["orderly", "image", "worker_name"])
        self.orderly_worker_ref = constellation.ImageReference(
            self.orderly_repo, self.orderly_worker_name, self.orderly_tag)

        # 4. Web
        self.web_repo = config.config_string(
            dat, ["web", "image", "repo"])
        self.web_name = config.config_string(
            dat, ["web", "image", "name"])
        self.web_tag = config.config_string(
            dat, ["web", "image", "tag"])
        self.web_ref = constellation.ImageReference(
            self.web_repo, self.web_name, self.web_tag)

        # 5. Admin
        self.admin_name = config.config_string(
            dat, ["web", "image", "admin"])
        self.admin_ref = constellation.ImageReference(
            self.web_repo, self.admin_name, self.web_tag)

        # 6. Migrate
        self.migrate_name = config.config_string(
            dat, ["web", "image", "migrate"])
        self.migrate_ref = constellation.ImageReference(
            self.web_repo, self.migrate_name, self.web_tag)

        self.containers = {
            # This silly name (redis_ow) is to avoid potential
            # collisions when running side-by-side with packit
            "redis": "redis-ow",
            "orderly": "orderly",
            "orderly-worker": "orderly-worker",
            "web": "web"
        }

        self.images = {
            "redis": self.redis_ref,
            "orderly": self.orderly_ref,
            "orderly-worker": self.orderly_worker_ref,
            "web": self.web_ref,
            "admin": self.admin_ref,
            "migrate": self.migrate_ref
        }

        # 7. Outpack
        self.outpack_enabled = "outpack" in dat
        if self.outpack_enabled:
            self.volumes["outpack"] = config.config_string(dat, ["volumes",
                                                                 "outpack"])
            self.outpack_repo = config.config_string(
                dat, ["outpack", "repo"])
            self.outpack_name = config.config_string(
                dat, ["outpack", "server", "name"])
            self.outpack_tag = config.config_string(
                dat, ["outpack", "server", "tag"])
            self.outpack_ref = constellation.ImageReference(
                self.outpack_repo, self.outpack_name,
                self.outpack_tag)

            self.outpack_migrate_name = config.config_string(
                dat, ["outpack", "migrate", "name"])
            self.outpack_migrate_tag = config.config_string(
                dat, ["outpack", "migrate", "tag"])
            self.outpack_migrate_ref = constellation.ImageReference(
                self.outpack_repo, self.outpack_migrate_name,
                self.outpack_migrate_tag)

            self.containers["outpack-server"] = "outpack-server"
            self.images["outpack-server"] = self.outpack_ref
            self.containers["outpack-migrate"] = "outpack-migrate"
            self.images["outpack-migrate"] = self.outpack_migrate_ref

        # 8. Packit
        if "packit" in dat and not self.outpack_enabled:
            print("Ignoring Packit configuration as outpack is not enabled")
        self.packit_enabled = "packit" in dat and self.outpack_enabled
        if self.packit_enabled:
            self.packit_repo = config.config_string(
                dat, ["packit", "repo"])

            self.packit_db_name = config.config_string(
                dat, ["packit", "db", "name"])
            self.packit_db_tag = config.config_string(
                dat, ["packit", "db", "tag"])
            self.packit_db_ref = constellation.ImageReference(
                self.packit_repo, self.packit_db_name,
                self.packit_db_tag)

            self.packit_api_name = config.config_string(
                dat, ["packit", "api", "name"])
            self.packit_api_tag = config.config_string(
                dat, ["packit", "api", "tag"])
            self.packit_api_ref = constellation.ImageReference(
                self.packit_repo, self.packit_api_name,
                self.packit_api_tag)

            self.packit_app_name = config.config_string(
                dat, ["packit", "app", "name"])
            self.packit_app_tag = config.config_string(
                dat, ["packit", "app", "tag"])
            self.packit_app_ref = constellation.ImageReference(
                self.packit_repo, self.packit_app_name,
                self.packit_app_tag)

            self.containers["packit-db"] = "packit-db"
            self.images["packit-db"] = self.packit_db_ref
            self.containers["packit-api"] = "packit-api"
            self.images["packit-api"] = self.packit_api_ref
            self.containers["packit"] = "packit"
            self.images["packit"] = self.packit_app_ref

        self.non_constellation_images = {
            "admin": self.admin_ref,
            "migrate": self.migrate_ref
        }

        self.orderly_env = config.config_dict(dat, ["orderly", "env"], True)
        self.orderly_expose = config.config_boolean(dat, ["orderly", "expose"],
                                                    True, False)

        self.web_dev_mode = config.config_boolean(
            dat, ["web", "dev_mode"], True)
        self.web_port = config.config_integer(dat, ["web", "port"])
        self.web_name = config.config_string(dat, ["web", "name"])
        self.web_email = config.config_string(dat, ["web", "email"])

        self.web_auth_montagu = config.config_boolean(
            dat, ["web", "auth", "montagu"])
        self.web_auth_fine_grained = config.config_boolean(
            dat, ["web", "auth", "fine_grained"])

        if not self.web_auth_montagu:
            self.web_auth_github_app = config.config_dict_strict(
                dat, ["web", "auth", "github_oauth"], ["id", "secret"])
            self.web_auth_github_org = config.config_string(
                dat, ["web", "auth", "github_org"])
            self.web_auth_github_team = config.config_string(
                dat, ["web", "auth", "github_team"], True)
        else:
            self.web_auth_github_app = None
            self.web_auth_github_org = None
            self.web_auth_github_team = None

        if self.web_auth_montagu:
            self.montagu_url = config.config_string(
                dat, ["web", "auth", "montagu_url"])
            self.montagu_api_url = config.config_string(
                dat, ["web", "auth", "montagu_api_url"])

        self.sass_variables = config.config_string(dat,
                                                   ["web", "sass_variables"],
                                                   True)
        self.logo_path = config.config_string(dat, ["web", "logo"], True)
        if self.logo_path is not None:
            self.logo_path = self.get_abs_path(self.logo_path)
            self.logo_name = os.path.basename(self.logo_path)
        else:
            self.logo_name = None

        self.favicon_path = config.config_string(dat, ["web", "favicon"], True)
        if self.favicon_path is not None:
            self.favicon_path = self.get_abs_path(self.favicon_path)

        if self.sass_variables is not None:
            variables_abspath = self.get_abs_path(self.sass_variables)
            self.sass_variables = variables_abspath
            self.volumes["css"] = config.config_string(dat, ["volumes", "css"])
            self.css_generator_name = config.config_string(
                dat, ["web", "image", "css-generator"])
            self.css_generator_ref = config.ImageReference(
                self.web_repo, self.css_generator_name, self.web_tag)
            self.images["css-generator"] = self.css_generator_ref
            self.non_constellation_images["css-generator"] = \
                self.css_generator_ref

        static_documents = config.config_string(
            dat, ["volumes", "documents"], True)
        if static_documents is not None:
            self.volumes["documents"] = static_documents

        if "proxy" in dat and dat["proxy"]:
            self.proxy_enabled = config.config_boolean(
                dat, ["proxy", "enabled"], True)

            if self.proxy_enabled:
                self.proxy_hostname = config.config_string(
                    dat, ["proxy", "hostname"])
                self.proxy_port_http = config.config_integer(
                    dat, ["proxy", "port_http"])
                self.proxy_port_https = config.config_integer(
                    dat, ["proxy", "port_https"])
                ssl = config.config_dict(dat, ["proxy", "ssl"], True)
                self.proxy_ssl_self_signed = ssl is None
                if not self.proxy_ssl_self_signed:
                    self.proxy_ssl_certificate = config.config_string(
                        dat, ["proxy", "ssl", "certificate"], True)
                    self.proxy_ssl_key = config.config_string(
                        dat, ["proxy", "ssl", "key"], True)

                self.proxy_repo = config.config_string(
                    dat, ["proxy", "image", "repo"])
                self.proxy_name = config.config_string(
                    dat, ["proxy", "image", "name"])
                self.proxy_tag = config.config_string(
                    dat, ["proxy", "image", "tag"])
                self.proxy_ref = constellation.ImageReference(
                    self.proxy_repo, self.proxy_name, self.proxy_tag)
                self.containers["proxy"] = "proxy"
                self.images["proxy"] = self.proxy_ref
                self.volumes["proxy_logs"] = config.config_string(
                    dat, ["volumes", "proxy_logs"])
        else:
            self.proxy_enabled = False

        self.web_url = config.config_string(dat, ["web", "url"], True)
        if not self.web_url:
            if self.proxy_enabled:
                self.web_url = "https://{}:{}".format(
                    self.proxy_hostname, self.proxy_port_https)
            elif self.web_dev_mode:
                self.web_url = "http://localhost:{}".format(self.web_port)
            else:
                raise Exception("web_url must be provided")

        self.orderly_ssh = config.config_dict_strict(
            dat, ["orderly", "ssh"], ["public", "private"], True)

        self.orderly_initial_source = None
        self.orderly_initial_url = None
        if "initial" in dat["orderly"] and dat["orderly"]["initial"]:
            self.orderly_initial_source = config.config_enum(
                dat, ["orderly", "initial", "source"], ["demo", "clone"])
            if self.orderly_initial_source == "clone":
                self.orderly_initial_url = config.config_string(
                    dat, ["orderly", "initial", "url"])
            elif "url" in dat["orderly"]["initial"]:
                # I think an error is a bit harsh
                print("NOTE: Ignoring orderly:initial:url")

        self.slack_webhook_url = config.config_string(dat,
                                                      ["slack", "webhook_url"],
                                                      True)

    def save(self):
        txt = base64.b64encode(pickle.dumps(self)).decode("utf8")
        container = self.get_container(PATH_CONFIG["container"])
        path = PATH_CONFIG["path"]
        docker_util.string_into_container(txt, container, path)

    def get_container(self, name):
        with docker_client() as cl:
            return cl.containers.get("{}-{}".format(self.container_prefix,
                                                    self.containers[name]))

    def resolve_secrets(self):
        vault_client = self.vault.client()
        vault.resolve_secrets(self.orderly_env, vault_client)
        vault.resolve_secrets(self.web_auth_github_app, vault_client)
        vault.resolve_secrets(self.orderly_ssh, vault_client)
        if self.slack_webhook_url is not None:
            _, self.slack_webhook_url = vault.resolve_secret(
                self.slack_webhook_url, vault_client)

    def get_abs_path(self, relative_path):
        return os.path.abspath(os.path.join(self.path, relative_path))
