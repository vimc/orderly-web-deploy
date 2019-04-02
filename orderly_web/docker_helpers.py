import math
import os
import tarfile
import tempfile
import time

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
        raise Exception("Error running command (see above for log)")
    return ans


def stop_and_remove_container(client, name, kill, timeout=10):
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
            container.stop(timeout=timeout)
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


def container_exists(client, name):
    try:
        client.containers.get(name)
        return True
    except docker.errors.NotFound:
        return False


# https://medium.com/@nagarwal/lifecycle-of-docker-container-d2da9f85959
def container_wait_running(container, poll=0.1, timeout=1):
    for i in range(math.ceil(timeout / poll)):
        if container.status != "created":
            break
        time.sleep(poll)
        container.reload()
    if container.status != "running":
        raise Exception("container '{}' ({}) is not running ({})".format(
            container.name, container.id[:8], container.status))
    time.sleep(timeout)
    container.reload()
    if container.status != "running":
        raise Exception("container '{}' ({}) was running but is now {}".format(
            container.name, container.id[:8], container.status))
    return container


def simple_tar(path, name):
    f = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode="w", fileobj=f)
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
# So this function assumes that the destination directory exists and
# dumps out text into a file in the container
def string_into_container(container, txt, dest):
    with simple_tar_string(txt, os.path.basename(dest)) as tar:
        container.put_archive(os.path.dirname(dest), tar)


# There is an annoyance with docker and the requests library, where
# when the http handle is reclaimed a warning is printed.  It makes
# the test log almost impossible to read.
#
# https://github.com/kennethreitz/requests/issues/1882#issuecomment-52281285
# https://github.com/kennethreitz/requests/issues/3912
#
# This little helper can be used with python's with statement as
#
#      with docker_client() as cl:
#        cl.containers...
#
# and will close *most* unused handles on exit.  It's easier to look
# at than endless try/finally blocks everywhere.
class docker_client():
    def __enter__(self):
        self.client = docker.client.from_env()
        return self.client

    def __exit__(self, type, value, traceback):
        self.client.close()
