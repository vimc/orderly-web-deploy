import docker


def return_logs_and_remove(client, image, args=None, mounts=None):
    try:
        container = client.containers.run(image, args, mounts=mounts,
                                          detach=True)
        container.wait()
        return container.logs().decode("UTF-8")
    finally:
        container.remove()


def read_env(container):
    return container.attrs["Config"]["Env"]


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
        pass
