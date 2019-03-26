from unittest import TestCase

from orderly_web.docker_helpers import *

class TestDockerHelpers(TestCase):

    def test_exec_safely_throws_on_failure(self):
        with docker_client() as cl:
            container = cl.containers.run("alpine", ["sleep", "10"],
                                          detach=True, auto_remove=True)
            with self.assertRaises(Exception):
                exec_safely(container, "missing_command")
            container.kill()

    def test_stop_and_remove_container_works(self):
        with docker_client() as cl:
            container = cl.containers.run("alpine", ["sleep", "10"],
                                          detach=True)
            name = container.name
            self.assertTrue(container_exists(cl, name))
            stop_and_remove_container(cl, name, False, 1)
            self.assertFalse(container_exists(cl, name))

    def test_string_into_container(self):
        with docker_client() as cl:
            container = cl.containers.run("alpine", ["sleep", "20"],
                                          detach=True, auto_remove=True)
            text = "a\nb\nc\n"
            string_into_container(container, text, "/test")
            out = container.exec_run(["cat", "/test"])
            self.assertEqual(out[0], 0)
            self.assertEqual(out[1].decode("UTF-8"), text)
            container.kill()
