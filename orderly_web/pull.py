from orderly_web.docker_helpers import docker_client


def pull(cfg):
    print("Pulling orderly-web images:")
    with docker_client() as cl:
        for name, repo in cfg.images.items():
            image = str(repo)
            print("  - {} ({})".format(name, image))
            img = cl.images.pull(str(image))
            print("    `-> {}".format(img.short_id))
