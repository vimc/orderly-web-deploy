from orderly_web.docker_helpers import docker_client


def pull(images):
    print("Pulling images:")
    with docker_client() as cl:
        for name, repo in images.items():
            image = str(repo)
            print("  - {} ({})".format(name, image))
            img = cl.images.pull(str(image))
            print("    `-> {}".format(img.short_id))
