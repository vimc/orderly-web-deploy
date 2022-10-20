import os
import tempfile
import docker

from PIL import Image

import constellation
import constellation.docker_util as docker_util

from orderly_web.docker_helpers import docker_client


def orderly_constellation(cfg):
    redis = redis_container(cfg)
    orderly = orderly_container(cfg, redis)
    worker = worker_container(cfg, redis)
    web = web_container(cfg)
    containers = [redis, orderly, worker, web]

    if cfg.proxy_enabled:
        proxy = proxy_container(cfg, web)
        containers.append(proxy)

    obj = constellation.Constellation("orderly-web", cfg.container_prefix,
                                      containers, cfg.network, cfg.volumes,
                                      data=cfg, vault_config=cfg.vault)
    return obj


def redis_container(cfg):
    redis_name = cfg.containers["redis"]
    redis_mounts = [constellation.ConstellationMount("redis", "/data")]
    redis_args = ["--appendonly", "yes"]
    redis = constellation.ConstellationContainer(
        redis_name, cfg.redis_ref, mounts=redis_mounts, args=redis_args,
        configure=redis_configure)
    return redis


def get_static_file(filename):
    package_directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(package_directory, "static", filename)


def redis_configure(container, cfg):
    print("[redis] Waiting for redis to come up")
    redis_script = get_static_file("wait_for_redis")
    docker_util.file_into_container(
        redis_script, container, ".", "wait_for_redis")
    docker_util.exec_safely(container, ["bash", "/wait_for_redis"])


def orderly_container(cfg, redis_container):
    orderly_name = cfg.containers["orderly"]
    orderly_args = ["--port", "8321", "--go-signal", "/go_signal", "/orderly"]
    orderly_mounts = [constellation.ConstellationMount("orderly", "/orderly")]
    orderly_env = {"REDIS_URL": "redis://{}:6379".format(
        redis_container.name_external(cfg.container_prefix))}
    orderly = constellation.ConstellationContainer(
        orderly_name, cfg.orderly_ref, args=orderly_args,
        mounts=orderly_mounts, environment=orderly_env,
        configure=orderly_configure, working_dir="/orderly")
    return orderly


def orderly_configure(container, cfg):
    orderly_write_ssh_keys(cfg.orderly_ssh, container)
    orderly_initial_data(cfg, container)
    orderly_check_schema(container)
    orderly_write_env(cfg.orderly_env, container)
    orderly_start(container)


def orderly_initial_data(cfg, container):
    if orderly_is_initialised(container):
        print("[orderly] orderly volume already contains data - "
              "not initialising")
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
    print("[orderly] Writing orderly environment")
    dest = "/root/.Renviron"
    txt = "".join(["{}={}\n".format(str(k), str(v)) for k, v in env.items()])
    docker_util.string_into_container(txt, container, dest)


def orderly_init_demo(container):
    print("[orderly] Initialising orderly with demo data")
    args = ["Rscript", "-e",
            "orderly:::create_orderly_demo('/orderly', git = TRUE)"]
    docker_util.exec_safely(container, args)


def orderly_init_clone(container, url):
    print("[orderly] Initialising orderly by cloning")
    args = ["git", "clone", url, "/orderly"]
    docker_util.exec_safely(container, args)


def orderly_is_initialised(container):
    res = container.exec_run(["stat", "/orderly/orderly_config.yml"])
    return res[0] == 0


def orderly_check_schema(container):
    print("[orderly] Checking orderly schema is current")
    docker_util.exec_safely(
        container, ["orderly", "rebuild", "--if-schema-changed"])


def orderly_write_ssh_keys(orderly_ssh, container):
    if not orderly_ssh:
        return
    print("[orderly] Configuring ssh")
    path_private = "/root/.ssh/id_rsa"
    path_public = "/root/.ssh/id_rsa.pub"
    path_known_hosts = "/root/.ssh/known_hosts"
    docker_util.exec_safely(container, ["mkdir", "-p", "/root/.ssh"])
    docker_util.string_into_container(
        orderly_ssh["private"], container, path_private)
    docker_util.string_into_container(
        orderly_ssh["public"], container, path_public)
    docker_util.exec_safely(container, ["chmod", "600", path_private])
    hosts = docker_util.exec_safely(container, ["ssh-keyscan", "github.com"])
    docker_util.string_into_container(hosts[1].decode("UTF-8"), container,
                                      path_known_hosts)


def orderly_start(container):
    print("[orderly] Starting orderly server")
    docker_util.exec_safely(container, ["touch", "/go_signal"])


def worker_container(cfg, redis_container):
    worker_name = cfg.containers["orderly_worker"]
    worker_args = ["--go-signal", "/go_signal"]
    worker_mounts = [constellation.ConstellationMount("orderly", "/orderly")]
    worker_env = {"REDIS_URL": "redis://{}:6379".format(
        redis_container.name_external(cfg.container_prefix))}
    worker_entrypoint = "/usr/local/bin/orderly_worker"
    worker = constellation.ConstellationService(
        worker_name, cfg.orderly_worker_ref, cfg.workers,
        args=worker_args, mounts=worker_mounts, environment=worker_env,
        entrypoint=worker_entrypoint, configure=worker_configure,
        working_dir="/orderly")
    return worker


def worker_configure(container, cfg):
    orderly_write_ssh_keys(cfg.orderly_ssh, container)
    orderly_write_env(cfg.orderly_env, container)
    worker_start(container)


def worker_start(container):
    print("[worker] Starting worker {}".format(container.name))
    docker_util.exec_safely(container, ["touch", "/go_signal"])


def web_container(cfg):
    web_name = cfg.containers["web"]
    web_mounts = [constellation.ConstellationMount("orderly", "/orderly")]
    if cfg.sass_variables is not None:
        web_mounts.append(constellation.ConstellationMount(
            "css", "/static/public/css"))
    if "documents" in cfg.volumes:
        web_mounts.append(constellation.ConstellationMount(
            "documents", "/documents"))
    if cfg.web_dev_mode:
        web_ports = [(cfg.web_port, ("127.0.0.1", cfg.web_port))]
    else:
        web_ports = None
    web = constellation.ConstellationContainer(
        web_name, cfg.web_ref, mounts=web_mounts, ports=web_ports,
        configure=web_configure)
    return web


def web_configure(container, cfg):
    if cfg.logo_name is not None:
        web_configure_logo(container, cfg)
    if cfg.sass_variables is not None:
        web_generate_css(cfg)
    if cfg.favicon_path is not None:
        img = generate_favicon(cfg.favicon_path)
        docker_util.file_into_container(img,
                                        container,
                                        "/static/public",
                                        "favicon.ico")
        os.remove(img)
    web_container_config(container, cfg)
    web_migrate(cfg)
    web_start(container)


def web_configure_logo(container, cfg):
    destination_path = "/static/public/img/logo/"
    docker_util.file_into_container(
        cfg.logo_path, container, destination_path, cfg.logo_name)


def web_generate_css(cfg):
    print("[web] Generating custom css")
    image = str(cfg.images["css-generator"])
    compiled_css_mount = \
        docker.types.Mount("/static/public/css", cfg.volumes["css"])
    variable_mount = \
        docker.types.Mount("/static/src/scss/partials/user-variables.scss",
                           cfg.sass_variables, type="bind")

    mounts = [compiled_css_mount, variable_mount]
    with docker_client() as cl:
        cl.containers.run(image, mounts=mounts, remove=True)


def generate_favicon(source):
    img = Image.open(source)
    fd, name = tempfile.mkstemp()
    img.save(name, format="ico")
    return name


def web_container_config(container, cfg):
    print("[web] Configuring web container")
    orderly_container = cfg.containers["orderly"]
    opts = {"app.port": str(cfg.web_port),
            "app.name": cfg.web_name,
            "app.email": cfg.web_email,
            "app.url": cfg.web_url,
            "auth.github_org": cfg.web_auth_github_org or "",
            "auth.github_team": cfg.web_auth_github_team or "",
            "auth.fine_grained": str(cfg.web_auth_fine_grained).lower(),
            "auth.provider": "montagu" if cfg.web_auth_montagu else "github",
            "orderly.server": "http://{}_{}:8321".format(cfg.container_prefix,
                                                         orderly_container)}
    if cfg.logo_name is not None:
        opts["app.logo"] = cfg.logo_name
    if cfg.web_auth_montagu:
        opts["montagu.url"] = cfg.montagu_url
        opts["montagu.api_url"] = cfg.montagu_api_url
    if cfg.web_auth_github_app:
        opts["auth.github_key"] = cfg.web_auth_github_app["id"]
        opts["auth.github_secret"] = cfg.web_auth_github_app["secret"]

    txt = "".join(["{}={}\n".format(k, v) for k, v in opts.items()])
    docker_util.exec_safely(container, ["mkdir", "-p", "/etc/orderly/web"])
    docker_util.string_into_container(
        txt, container, "/etc/orderly/web/config.properties")


def web_migrate(cfg):
    print("[web] Migrating the web tables")
    image = str(cfg.images["migrate"])
    mounts = [docker.types.Mount("/orderly", cfg.volumes["orderly"])]
    with docker_client() as cl:
        cl.containers.run(image, mounts=mounts, remove=True)


def web_start(container):
    print("[web] Starting OrderlyWeb")
    docker_util.exec_safely(container, ["touch", "/etc/orderly/web/go_signal"])


def proxy_container(cfg, web_container):
    print("[proxy] Creating proxy container")
    proxy_name = cfg.containers["proxy"]
    web_addr = "{}:{}".format(
        web_container.name_external(cfg.container_prefix), cfg.web_port)
    proxy_args = [cfg.proxy_hostname, str(cfg.proxy_port_http),
                  str(cfg.proxy_port_https), web_addr]
    proxy_mounts = [constellation.ConstellationMount(
        "proxy_logs", "/var/log/nginx")]
    proxy_ports = [cfg.proxy_port_http, cfg.proxy_port_https]
    proxy = constellation.ConstellationContainer(
        proxy_name, cfg.proxy_ref, ports=proxy_ports, args=proxy_args,
        mounts=proxy_mounts, configure=proxy_configure)
    return proxy


def proxy_configure(container, cfg):
    if cfg.proxy_ssl_self_signed:
        print("[proxy] Generating self-signed certificates for proxy")
        docker_util.exec_safely(
            container, ["self-signed-certificate", "/run/proxy"])
    else:
        print("[proxy] Copying ssl certificate and key into proxy")
        docker_util.string_into_container(cfg.proxy_ssl_certificate, container,
                                          "/run/proxy/certificate.pem")
        docker_util.string_into_container(cfg.proxy_ssl_key, container,
                                          "/run/proxy/key.pem")
