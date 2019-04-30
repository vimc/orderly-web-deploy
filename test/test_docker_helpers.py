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
        string_into_container(text, container, "/test")
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
        assert "was running but is now exited" in str(e)


def test_container_wait_running_returns_cintainer():
    with docker_client() as cl:
        container = cl.containers.run("alpine", ["sleep", "100"], detach=True)
        res = container_wait_running(container, 0.1, 1.2)
        assert res == container
        container.kill()
        container.remove()


def test_that_removing_missing_container_is_harmless():
    with docker_client() as cl:
        nm = "orderly_web_noncontainer"
        stop_and_remove_container(cl, nm, True)


def test_that_removing_missing_network_is_harmless():
    with docker_client() as cl:
        nm = "orderly_web_nonnetwork"
        remove_network(cl, nm)


def test_that_removing_missing_volume_is_harmless():
    with docker_client() as cl:
        nm = "orderly_web_nonvolume"
        remove_volume(cl, nm)
