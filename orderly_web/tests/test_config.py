from unittest import TestCase

from orderly_web.config import config_string, config_integer, config_boolean


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
