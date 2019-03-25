from unittest import TestCase

from orderly_web.config import config_string

class TestConfigHelpers(TestCase):
    sample_data = {"a": "value1", "b": {"x": "value2"}, "c": 1}
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
