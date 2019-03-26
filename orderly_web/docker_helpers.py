import os
import tarfile
import tempfile

import docker


def ensure_network(client, name):
    try:
        client.networks.get(name)
    except docker.errors.NotFound:
        print("Creating docker network '{}'".format(name))
        client.networks.create(name)


def ensure_volume(client, name):
    try:
        client.volumes.get(name)
    except docker.errors.NotFound:
        print("Creating docker volume '{}'".format(name))
        client.volumes.create(name)


def exec_safely(container, args):
    ans = container.exec_run(args)
    if ans[0] != 0:
        print(ans[1].decode("UTF-8"))
        raise Exception("Error running demo command (see above for log)")


def stop_and_remove_container(client, name, kill):
    try:
        container = client.containers.get(name)
    except docker.errors.NotFound:
        return
    if container.status == "running":
        if kill:
            print("Killing '{}'".format(name))
            container.kill()
        else:
            print("Stopping '{}'".format(name))
            container.stop()
    print("Removing '{}'".format(name))
    container.remove()


def remove_network(client, name):
    try:
        nw = client.networks.get(name)
    except docker.errors.NotFound:
        return
    print("Removing network '{}'".format(name))
    nw.remove()


def remove_volume(client, name):
    try:
        v = client.volumes.get(name)
    except docker.errors.NotFound:
        return
    print("Removing volume '{}'".format(name))
    v.remove(name)


def simple_tar(path, name):
    f = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode="w", fileobj=f)
    if not name:
        name = os.path.basename(path)
    abs_path = os.path.abspath(path)
    t.add(abs_path, arcname=name, recursive=False)
    t.close()
    f.seek(0)
    return f


def simple_tar_string(text, name):
    try:
        fd, tmp = tempfile.mkstemp(text=True)
        with os.fdopen(fd, "w") as f:
            f.write(text)
        return simple_tar(tmp, name)
    finally:
        os.remove(tmp)


# The python docker client does not provide nice 'docker cp' wrappers
# (https://github.com/docker/docker-py/issues/1771) - so we have to
# roll our own.  These are a real pain to do "properly".  For example
# see
# https://github.com/richfitz/stevedore/blob/845587/R/docker_client_support.R#L943-L1020
#
# So these functions assume that the destination directory exists and
# can copy either a file or the contents of a string into a container.
def cp_into_container(container, src, dest):
    with simple_tar(src, os.path.basename(dest)) as tar:
        container.put_archive(os.path.dirname(dest), tar)


def string_into_container(container, txt, dest):
    with simple_tar_string(txt, os.path.basename(dest)) as tar:
        container.put_archive(os.path.dirname(dest), tar)
