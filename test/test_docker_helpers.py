import pytest

from orderly_web.docker_helpers import *


def test_exec_safely_throws_on_failure():
    with docker_client() as cl:
        container = cl.containers.run("alpine", ["sleep", "10"],
                                      detach=True, auto_remove=True)
        with pytest.raises(Exception):
            exec_safely(container, "missing_command")
        container.kill()

def test_stop_and_remove_container_works():
    with docker_client() as cl:
        container = cl.containers.run("alpine", ["sleep", "10"],
                                      detach=True)
        name = container.name
        assert container_exists(cl, name)
        stop_and_remove_container(cl, name, False, 1)
        assert not container_exists(cl, name)

def test_string_into_container():
    with docker_client() as cl:
        container = cl.containers.run("alpine", ["sleep", "20"],
                                      detach=True, auto_remove=True)
        text = "a\nb\nc\n"
        string_into_container(container, text, "/test")
        out = container.exec_run(["cat", "/test"])
        assert out[0] == 0
        assert out[1].decode("UTF-8") == text
        container.kill()


def test_container_wait_running_detects_start_failure():
    with docker_client() as cl:
        container = cl.containers.create("alpine")
        with pytest.raises(Exception) as e:
            container_wait_running(container, 0.1, 0.1)
        assert "is not running (created)" in str(e)


def test_container_wait_running_detects_slow_failure():
    with docker_client() as cl:
        with pytest.raises(Exception) as e:
            container = cl.containers.run("alpine", ["sleep", "1"],
                                          detach=True)
            container_wait_running(container, 0.1, 1.2)
        assert "is no longer running (exited)" in str(e)
