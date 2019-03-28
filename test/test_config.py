from unittest import TestCase

from orderly_web.config import config_string, config_integer, config_boolean, \
    config_image_reference, read_config, DockerImageReference


class TestConfigHelpers(TestCase):
    sample_data = {"a": "value1", "b": {"x": "value2"}, "c": 1, "d": True}

    def test_config_string_reads_simple_values(self):
        self.assertEqual(config_string(self.sample_data, "a"), "value1")
        self.assertEqual(config_string(self.sample_data, ["a"]), "value1")

    def test_config_string_reads_nested_values(self):
        self.assertEqual(config_string(self.sample_data, ["b", "x"]), "value2")

    def test_config_string_throws_on_missing_keys(self):
        with self.assertRaises(KeyError):
            config_string(self.sample_data, "x")
        with self.assertRaises(KeyError):
            config_string(self.sample_data, ["b", "y"])

    def test_config_string_validates_types(self):
        with self.assertRaises(ValueError):
            config_string(self.sample_data, "c")

    def test_config_string_default(self):
        self.assertIsNone(config_string(self.sample_data, "x", True))

    def test_config_integer(self):
        self.assertEqual(config_integer(self.sample_data, "c"), 1)

    def test_config_boolean(self):
        self.assertEqual(config_boolean(self.sample_data, "d"), True)


class TestExampleConfig(TestCase):
    def test_example_config(self):
        cfg = read_config("example")
        self.assertEqual(cfg.network, "orderly_web_network")
        self.assertEqual(cfg.volumes["orderly"], "orderly_web_volume")
        self.assertEqual(cfg.containers["orderly"], "orderly_web_orderly")
        self.assertEqual(cfg.containers["web"], "orderly_web_web")

        self.assertEqual(cfg.images["orderly"].repo, "vimc")
        self.assertEqual(cfg.images["orderly"].name, "orderly.server")
        self.assertEqual(cfg.images["orderly"].tag, "master")
        self.assertEqual(str(cfg.images["orderly"]),
                         "vimc/orderly.server:master")
        self.assertEqual(cfg.web_dev_mode, True)
        self.assertEqual(cfg.web_port, 8888)
        self.assertEqual(cfg.web_name, "OrderlyWeb")
        self.assertEqual(cfg.web_email, "admin@example.com")
        self.assertEqual(cfg.web_auth_montagu, False)
        self.assertEqual(cfg.web_auth_fine_grained, True)
        self.assertEqual(cfg.web_auth_github_org, "vimc")
        self.assertEqual(cfg.web_auth_github_team, "")


class TestDockerImageReference(TestCase):
    def test_string_representation(self):
        img = DockerImageReference("a", "b", "c")
        self.assertEqual(str(img), "a/b:c")

    def test_config_image_reference(self):
        data = {"foo": {
            "repo": "a", "name": "b", "tag": "c", "other": "d", "num": 1}}
        self.assertEqual(str(config_image_reference(data, "foo")),
                         "a/b:c")
        self.assertEqual(str(config_image_reference(data, ["foo"], "other")),
                         "a/d:c")
        with self.assertRaises(KeyError):
            config_image_reference(data, ["foo"], "missing")
        with self.assertRaises(ValueError):
            config_image_reference(data, ["foo"], "num")
