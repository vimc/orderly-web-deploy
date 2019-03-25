import docker

from orderly_web.docker_helpers import exec_safely

def deploy(cfg):
    docker_client = docker.client.from_env()


def orderly_init(cfg, docker_client):
    container = orderly_container(cfg, docker_client)
    if not orderly_is_initialised(container):
        orderly_init_demo(container)
    orderly_check_schema(container)
    orderly_start_server(container)
    return container


def orderly_container(cfg, docker_client):
    print("Creating orderly container")
    args = ["--port", "8321", "--go-signal", "/orderly_go", "/orderly"]
    mounts = [docker.types.Mount("/orderly", cfg.volumes["orderly"])]
    container = docker_client.containers.run(
        cfg.orderly_image, args, mounts=mounts, network=cfg.network,
        name=cfg.orderly_name, working_dir="/orderly", detach=True)
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


def orderly_start_server(container):
    print("Starting orderly server")
    exec_safely(container, ["touch", "/orderly_go"])
