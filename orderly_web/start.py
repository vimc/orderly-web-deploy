import docker

from orderly_web.status import status
from orderly_web.docker_helpers import docker_client, \
    ensure_network, ensure_volume, \
    exec_safely, string_into_container


def start(cfg):
    st = status(cfg)
    for name, data in st.containers.items():
        if data["status"] is not "missing":
            msg = "Container '{}' is {}; please run orderly-web stop".format(
                name, data["status"])
            print(msg)
            return False
    with docker_client() as cl:
        ensure_network(cl, cfg.network)
        for v in cfg.volumes.values():
            ensure_volume(cl, v)
        orderly = orderly_init(cfg, cl)
        web = web_init(cfg, cl)
        return True

def orderly_init(cfg, docker_client):
    container = orderly_container(cfg, docker_client)
    if not orderly_is_initialised(container):
        orderly_init_demo(container)
    orderly_check_schema(container)
    orderly_start(container)
    return container


def orderly_container(cfg, docker_client):
    print("Creating orderly container")
    args = ["--port", "8321", "--go-signal", "/go_signal", "/orderly"]
    image = str(cfg.images["orderly"])
    mounts = [docker.types.Mount("/orderly", cfg.volumes["orderly"])]
    container = docker_client.containers.run(
        image, args, mounts=mounts, network=cfg.network,
        name=cfg.containers["orderly"], working_dir="/orderly", detach=True)
    return container


def orderly_init_demo(container):
    print("Initialising orderly with demo data")
    args = ["Rscript", "-e", "orderly:::create_orderly_demo('/orderly')"]
    exec_safely(container, args)


def orderly_is_initialised(container):
    res = container.exec_run(["stat", "/orderly/orderly_config.yml"])
    return res[0] == 0


def orderly_check_schema(container):
    print("Checking orderly schema is current")
    exec_safely(container, ["orderly", "rebuild", "--if-schema-changed"])


def orderly_start(container):
    print("Starting orderly server")
    exec_safely(container, ["touch", "/go_signal"])


def web_init(cfg, docker_client):
    container = web_container(cfg, docker_client)
    web_container_config(cfg, container)
    web_migrate(cfg, docker_client)
    web_start(container)
    return container


def web_container(cfg, docker_client):
    print("Creating web container")
    image = str(cfg.images["web"])
    mounts = [docker.types.Mount("/orderly", cfg.volumes["orderly"])]
    if cfg.web_dev_mode:
        port = cfg.web_port
        ports = {"{}/tcp".format(port): ("127.0.0.1", port)}
    else:
        ports = None
    container = docker_client.containers.run(
        image, mounts=mounts, network=cfg.network, ports=ports,
        name=cfg.containers["web"], detach=True)
    return container


def web_container_config(cfg, container):
    print("Configuring web container")
    opts = {"app.port": str(cfg.web_port),
            "app.name": cfg.web_name,
            "app.email": cfg.web_email,
            "app.github_org": cfg.web_auth_github_org,
            "app.github_team": cfg.web_auth_github_team,
            "app.auth": str(cfg.web_auth_fine_grained).lower(),
            "orderly.server": "{}:8321".format(cfg.containers["orderly"])}
    txt = "".join(["{}={}\n".format(k, v) for k, v in opts.items()])
    exec_safely(container, ["mkdir", "-p", "/etc/orderly/web"])
    string_into_container(container, txt, "/etc/orderly/web/config.properties")


def web_migrate(cfg, docker_client):
    print("Migrating the web tables")
    image = str(cfg.images["migrate"])
    mounts = [docker.types.Mount("/orderly", cfg.volumes["orderly"])]
    docker_client.containers.run(image, mounts=mounts, auto_remove=True)


def web_start(container):
    print("Starting orderly server")
    exec_safely(container, ["touch", "/etc/orderly/web/go_signal"])
