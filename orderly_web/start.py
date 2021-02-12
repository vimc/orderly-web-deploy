import os
import tempfile
import random
import string

import docker
from PIL import Image

from orderly_web.config import build_config
from orderly_web.notify import Notifier
from orderly_web.status import status
from orderly_web.pull import pull
from orderly_web.docker_helpers import docker_client, \
    ensure_network, ensure_volume, container_wait_running, \
    exec_safely, string_into_container, file_into_container


def start(path, extra=None, options=None, pull_images=False):
    st = status(path)
    for name, data in st.containers.items():
        if data["status"] != "missing":
            msg = "Container '{}' is {}; please run orderly-web stop".format(
                name, data["status"])
            print(msg)
            return False
    cfg = build_config(path, extra, options)
    cfg.resolve_secrets()
    if pull_images:
        pull(cfg)

    notifier = Notifier(cfg.slack_webhook_url)
    with docker_client() as cl:
        notifier.post("*Starting* deploy to {}".format(cfg.web_url))
        try:
            init_all(cl, cfg)
            notifier.post("*Completed* deploy to {} :shipit:"
                          .format(cfg.web_url))
            return True
        except Exception:
            notifier.post("*Failed* deploy to {} :bomb:".format(cfg.web_url))
            raise


def init_all(cl, cfg):
    ensure_network(cl, cfg.network)
    for v in cfg.volumes.values():
        ensure_volume(cl, v)
    redis_init(cfg, cl)
    orderly_init(cfg, cl)
    worker_init(cfg, cl)
    web_init(cfg, cl)
    proxy_init(cfg, cl)
    config_save(cfg)


def rand_str(n, prefix=""):
    s = "".join(random.choice(string.ascii_lowercase) for i in range(n))
    return prefix + s


def redis_init(cfg, docker_client):
    print("Creating redis container")
    args = ["--appendonly", "yes"]
    image = str(cfg.images["redis"])
    mounts = [docker.types.Mount("/redis-data", cfg.volumes["redis"])]
    container = docker_client.containers.run(
        image, args, mounts=mounts, network="none",
        name=cfg.containers["redis"], detach=True)
    docker_client.networks.get("none").disconnect(container)
    docker_client.networks.get(cfg.network).connect(container,
                                                    aliases=["redis"])
    return container


def orderly_init(cfg, docker_client):
    container = orderly_container(cfg, docker_client)
    orderly_write_ssh_keys(cfg.orderly_ssh, container)
    orderly_initial_data(cfg, container)
    orderly_check_schema(container)
    orderly_write_env(cfg.orderly_env, container)
    orderly_start(container)
    return container


def orderly_container(cfg, docker_client):
    print("Creating orderly container")
    args = ["--port", "8321", "--go-signal", "/go_signal", "/orderly"]
    image = str(cfg.images["orderly"])
    mounts = [docker.types.Mount("/orderly", cfg.volumes["orderly"])]
    orderly_env = {"REDIS_URL": "redis://redis:6379"}
    container = docker_client.containers.run(
        image, args, mounts=mounts, network=cfg.network,
        name=cfg.containers["orderly"], working_dir="/orderly", detach=True,
        environment=orderly_env)
    return container


def orderly_initial_data(cfg, container):
    if orderly_is_initialised(container):
        print("orderly volume already contains data - not initialising")
    else:
        if cfg.orderly_initial_source == "demo":
            orderly_init_demo(container)
        elif cfg.orderly_initial_source == "clone":
            orderly_init_clone(container, cfg.orderly_initial_url)
        else:
            raise Exception("Orderly volume not initialised")


def orderly_write_env(env, container):
    if not env:
        return
    print("Writing orderly environment")
    dest = "/root/.Renviron"
    txt = "".join(["{}={}\n".format(str(k), str(v)) for k, v in env.items()])
    string_into_container(txt, container, dest)


def orderly_init_demo(container):
    print("Initialising orderly with demo data")
    args = ["Rscript", "-e", "orderly:::create_orderly_demo('/orderly')"]
    exec_safely(container, args)


def orderly_init_clone(container, url):
    print("Initialising orderly by cloning")
    args = ["git", "clone", url, "/orderly"]
    exec_safely(container, args)


def orderly_is_initialised(container):
    res = container.exec_run(["stat", "/orderly/orderly_config.yml"])
    return res[0] == 0


def orderly_check_schema(container):
    print("Checking orderly schema is current")
    exec_safely(container, ["orderly", "rebuild", "--if-schema-changed"])


def orderly_write_ssh_keys(orderly_ssh, container):
    if not orderly_ssh:
        return
    print("Configuring ssh")
    path_private = "/root/.ssh/id_rsa"
    path_public = "/root/.ssh/id_rsa.pub"
    path_known_hosts = "/root/.ssh/known_hosts"
    exec_safely(container, ["mkdir", "-p", "/root/.ssh"])
    string_into_container(orderly_ssh["private"], container, path_private)
    string_into_container(orderly_ssh["public"], container, path_public)
    exec_safely(container, ["chmod", "600", path_private])
    hosts = exec_safely(container, ["ssh-keyscan", "github.com"])
    string_into_container(hosts[1].decode("UTF-8"), container,
                          path_known_hosts)


def orderly_start(container):
    print("Starting orderly server")
    exec_safely(container, ["touch", "/go_signal"])


def worker_init(cfg, docker_client):
    workers = worker_container(cfg, docker_client)
    for worker in workers:
        orderly_write_ssh_keys(cfg.orderly_ssh, worker)
        orderly_write_env(cfg.orderly_env, worker)
        worker_start(worker)
    return workers


def worker_container(cfg, docker_client):
    scale = cfg.container_groups["orderly_worker"]["scale"]
    print("Starting {} orderly workers".format(scale))
    image = str(cfg.images["orderly_worker"])
    args = ["--go-signal", "/go_signal"]
    mounts = [docker.types.Mount("/orderly", cfg.volumes["orderly"])]
    worker_env = {"REDIS_URL": "redis://redis:6379"}
    worker_entrypoint = "/usr/local/bin/orderly_worker"
    workers = []
    for i in range(scale):
        name = "{}_{}".format(cfg.container_groups["orderly_worker"]["name"],
                              rand_str(8))
        container = docker_client.containers.run(
            image, args, mounts=mounts, network=cfg.network,
            name=name, working_dir="/orderly", detach=True,
            environment=worker_env, entrypoint=worker_entrypoint)
        workers.append(container)
    return workers


def worker_start(container):
    print("Starting worker {}".format(container.name))
    exec_safely(container, ["touch", "/go_signal"])


def web_init(cfg, docker_client):
    if cfg.sass_variables is not None:
        web_generate_css(cfg, docker_client)
    container = web_container(cfg, docker_client)
    web_container_config(cfg, container)
    web_migrate(cfg, docker_client)
    web_start(container)
    return container


def web_container(cfg, docker_client):
    print("Creating web container")
    image = str(cfg.images["web"])
    mounts = [docker.types.Mount("/orderly", cfg.volumes["orderly"])]
    if cfg.sass_variables is not None:
        mounts.append(docker.types.Mount("/static/public/css",
                                         cfg.volumes["css"]))
    if cfg.logo_name is not None:
        logo_in_container = "/static/public/img/logo/{}".format(cfg.logo_name)
        mounts.append(docker.types.Mount(logo_in_container,
                                         cfg.logo_path,
                                         type="bind"))
    if "documents" in cfg.volumes:
        mounts.append(docker.types.Mount("/documents",
                                         cfg.volumes["documents"]))
    if cfg.web_dev_mode:
        port = cfg.web_port
        # NOTE: different format to proxy below because we only
        # expose this to the localhost, and not to any external
        # interface
        ports = {"{}/tcp".format(cfg.web_port): ("127.0.0.1", cfg.web_port)}
    else:
        ports = None
    container = docker_client.containers.run(
        image, mounts=mounts, network=cfg.network, ports=ports,
        name=cfg.containers["web"], detach=True)
    if cfg.favicon_path is not None:
        img = generate_favicon(cfg.favicon_path)
        file_into_container(img,
                            container,
                            "/static/public",
                            "favicon.ico")
        os.remove(img)
    return container


def generate_favicon(source):
    img = Image.open(source)
    fd, name = tempfile.mkstemp()
    img.save(name, format="ico")
    return name


def web_container_config(cfg, container):
    print("Configuring web container")
    orderly_container = cfg.containers["orderly"]
    opts = {"app.port": str(cfg.web_port),
            "app.name": cfg.web_name,
            "app.email": cfg.web_email,
            "app.url": cfg.web_url,
            "auth.github_org": cfg.web_auth_github_org or "",
            "auth.github_team": cfg.web_auth_github_team or "",
            "auth.fine_grained": str(cfg.web_auth_fine_grained).lower(),
            "auth.provider": "montagu" if cfg.web_auth_montagu else "github",
            "orderly.server": "http://{}:8321".format(orderly_container)}
    if cfg.logo_name is not None:
        opts["app.logo"] = cfg.logo_name
    if cfg.web_auth_montagu:
        opts["montagu.url"] = cfg.montagu_url
        opts["montagu.api_url"] = cfg.montagu_api_url
    if cfg.web_auth_github_app:
        opts["auth.github_key"] = cfg.web_auth_github_app["id"]
        opts["auth.github_secret"] = cfg.web_auth_github_app["secret"]

    txt = "".join(["{}={}\n".format(k, v) for k, v in opts.items()])
    exec_safely(container, ["mkdir", "-p", "/etc/orderly/web"])
    string_into_container(txt, container, "/etc/orderly/web/config.properties")


def web_migrate(cfg, docker_client):
    print("Migrating the web tables")
    image = str(cfg.images["migrate"])
    mounts = [docker.types.Mount("/orderly", cfg.volumes["orderly"])]
    docker_client.containers.run(image, mounts=mounts, remove=True)


def web_generate_css(cfg, docker_client):
    print("Generating custom css")
    image = str(cfg.images["css-generator"])
    compiled_css_mount = \
        docker.types.Mount("/static/public/css", cfg.volumes["css"])
    variable_mount = \
        docker.types.Mount("/static/src/scss/partials/user-variables.scss",
                           cfg.sass_variables, type="bind")

    mounts = [compiled_css_mount, variable_mount]
    docker_client.containers.run(image, mounts=mounts, remove=True)


def web_start(container):
    print("Starting orderly server")
    exec_safely(container, ["touch", "/etc/orderly/web/go_signal"])


def proxy_init(cfg, docker_client):
    if not cfg.proxy_enabled:
        return
    container = proxy_container(cfg, docker_client)
    proxy_certificates(cfg, container)


def proxy_container(cfg, docker_client):
    print("Creating proxy container")
    image = str(cfg.images["proxy"])
    orderly = "{}:{}".format(cfg.containers["web"], cfg.web_port)
    args = [cfg.proxy_hostname, str(cfg.proxy_port_http),
            str(cfg.proxy_port_https), orderly]
    mounts = [docker.types.Mount("/var/log/nginx", cfg.volumes["proxy_logs"])]
    ports = {
        "{}/tcp".format(cfg.proxy_port_http): cfg.proxy_port_http,
        "{}/tcp".format(cfg.proxy_port_https): cfg.proxy_port_https
    }
    ret = docker_client.containers.run(
        image, args, detach=True, name=cfg.containers["proxy"],
        network=cfg.network, mounts=mounts, ports=ports)
    return container_wait_running(ret)


def proxy_certificates(cfg, container):
    if cfg.proxy_ssl_self_signed:
        print("Generating self-signed certificates for proxy")
        exec_safely(container, ["self-signed-certificate", "/run/proxy"])
    else:
        print("Copying ssl certificate and key into proxy")
        string_into_container(cfg.proxy_ssl_certificate, container,
                              "/run/proxy/certificate.pem")
        string_into_container(cfg.proxy_ssl_key, container,
                              "/run/proxy/key.pem")


def config_save(cfg):
    print("Persisting configuration")
    cfg.save()
