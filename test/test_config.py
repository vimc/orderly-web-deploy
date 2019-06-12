import pytest
import shutil
import tempfile
import vault_dev
import yaml
import os

from orderly_web.config import *

sample_data = {"a": "value1", "b": {"x": "value2"}, "c": 1, "d": True,
               "e": None}


def test_config_string_reads_simple_values():
    assert config_string(sample_data, "a") == "value1"
    assert config_string(sample_data, ["a"]) == "value1"


def test_config_string_reads_nested_values():
    assert config_string(sample_data, ["b", "x"]) == "value2"


def test_config_string_throws_on_missing_keys():
    with pytest.raises(KeyError):
        config_string(sample_data, "x")
    with pytest.raises(KeyError):
        config_string(sample_data, ["b", "y"])


def test_config_none_is_missing():
    with pytest.raises(KeyError):
        config_string(sample_data, ["e"], False)
    assert config_string(sample_data, ["e"], True) is None


def test_config_string_validates_types():
    with pytest.raises(ValueError):
        config_string(sample_data, "c")


def test_config_string_default():
    assert config_string(sample_data, "x", True) is None


def test_config_integer():
    assert config_integer(sample_data, "c") == 1


def test_config_boolean():
    assert config_boolean(sample_data, "d")


def test_example_config():
    cfg = build_config("config/basic")
    assert cfg.network == "orderly_web_network"
    assert cfg.volumes["orderly"] == "orderly_web_volume"
    assert cfg.containers["orderly"] == "orderly_web_orderly"
    assert cfg.containers["web"] == "orderly_web_web"

    assert cfg.images["orderly"].repo == "vimc"
    assert cfg.images["orderly"].name == "orderly.server"
    assert cfg.images["orderly"].tag == "master"
    assert str(cfg.images["orderly"]) == "vimc/orderly.server:master"
    assert cfg.web_dev_mode
    assert cfg.web_port == 8888
    assert cfg.web_name == "OrderlyWeb"
    assert cfg.web_email == "admin@example.com"
    assert not cfg.web_auth_montagu
    assert cfg.web_auth_fine_grained
    assert cfg.web_auth_github_org == "vimc"
    assert cfg.web_auth_github_team == ""
    assert cfg.sass_variables is None
    assert "css-generator" not in cfg.images
    assert "css" not in cfg.volumes
    assert cfg.logo_name is None
    assert cfg.logo_path is None

    assert cfg.proxy_enabled
    assert cfg.proxy_ssl_self_signed
    assert str(cfg.images["proxy"]) == "vimc/orderly-web-proxy:master"


def test_config_custom_styles():
    path = "config/customcss"
    cfg = build_config(path)
    expected_path = os.path.abspath(os.path.join(cfg.path, "variables.scss"))
    assert cfg.sass_variables == expected_path
    assert cfg.volumes["css"] == "orderly_web_css"
    assert cfg.images["css-generator"].repo == "vimc"
    assert cfg.images["css-generator"].name == "orderly-web-css-generator"
    assert cfg.images["css-generator"].tag == "master"
    assert cfg.logo_name == "my-test-logo.png"
    expected_path = os.path.abspath(os.path.join(cfg.path, "my-test-logo.png"))
    assert cfg.logo_path == expected_path


def test_string_representation():
    img = DockerImageReference("a", "b", "c")
    assert str(img) == "a/b:c"


def test_config_image_reference():
    data = {"foo": {
        "repo": "a", "name": "b", "tag": "c", "other": "d", "num": 1}}
    assert str(config_image_reference(data, "foo")) == "a/b:c"
    assert str(config_image_reference(data, ["foo"], "other")) == "a/d:c"
    with pytest.raises(KeyError):
        config_image_reference(data, ["foo"], "missing")
    with pytest.raises(ValueError):
        config_image_reference(data, ["foo"], "num")


def test_config_no_proxy():
    cfg = build_config("config/noproxy")
    assert not cfg.proxy_enabled


def test_can_substitute_secrets():
    with vault_dev.server() as s:
        cl = s.client()
        # Copy the certificates into the vault where we will later on
        # pull from from.
        cert = read_file("proxy/ssl/certificate.pem")
        key = read_file("proxy/ssl/key.pem")
        cl.write("secret/ssl/certificate", value=cert)
        cl.write("secret/ssl/key", value=key)
        cl.write("secret/db/password", value="s3cret")

        # When reading the configuration we have to interpolate in the
        # correct values here for the vault connection
        cfg = build_config("config/complete")
        cfg.vault.url = "http://localhost:{}".format(s.port)
        cfg.vault.auth_args["token"] = s.token

        cfg.resolve_secrets()
        assert not cfg.proxy_ssl_self_signed
        assert cfg.proxy_ssl_certificate == cert
        assert cfg.proxy_ssl_key == key
        assert cfg.orderly_env["ORDERLY_DB_PASS"] == "s3cret"


def test_combine():
    def do_combine(a, b):
        """lets us use combine with unnamed data"""
        combine(a, b)
        return a

    assert do_combine({"a": 1}, {"b": 2}) == \
        {"a": 1, "b": 2}
    assert do_combine({"a": {"x": 1}, "b": 2}, {"a": {"x": 3}}) == \
        {"a": {"x": 3}, "b": 2}
    assert do_combine({"a": {"x": 1, "y": 4}, "b": 2}, {"a": {"x": 3}}) == \
        {"a": {"x": 3, "y": 4}, "b": 2}
    assert do_combine({"a": None, "b": 2}, {"a": {"x": 3}}) == \
        {"a": {"x": 3}, "b": 2}


def test_read_and_extra():
    with tempfile.TemporaryDirectory() as p:
        shutil.copy("config/basic/orderly-web.yml", p)
        with open("{}/patch.yml".format(p), "w+") as f:
            data = {"network": "patched_network"}
            yaml.dump(data, f)
        cfg = build_config(p, "patch")
        assert cfg.network == "patched_network"


def test_read_and_options():
    options = {"network": "patched_network"}
    cfg = build_config("config/basic", options=options)
    assert cfg.network == "patched_network"


def test_read_complex():
    with tempfile.TemporaryDirectory() as p:
        shutil.copy("config/basic/orderly-web.yml", p)
        data1 = {"network": "network1",
                 "volumes": {"proxy_logs": "mylogs"}}
        data2 = {"network": "network2",
                 "volumes": {"orderly": "mydata"}}
        with open("{}/patch.yml".format(p), "w+") as f:
            data = {"network": "patched_network"}
            yaml.dump(data1, f)
        cfg = build_config(p, "patch", data2)
        assert cfg.network == "network2"
        assert cfg.volumes["orderly"] == "mydata"
        assert cfg.volumes["proxy_logs"] == "mylogs"


def test_cant_overwrite_prefix_with_patch():
    with tempfile.TemporaryDirectory() as p:
        shutil.copy("config/basic/orderly-web.yml", p)
        with open("{}/patch.yml".format(p), "w+") as f:
            data = {"container_prefix": "patched_orderly_web"}
            yaml.dump(data, f)
        with pytest.raises(Exception,
                           match="'container_prefix' may not be modified"):
            build_config(p, "patch")


def test_cant_overwrite_prefix_with_options():
    with pytest.raises(Exception,
                       match="'container_prefix' may not be modified"):
        options = {"container_prefix": "patched_orderly_web"}
        build_config("config/basic", options=options)


def test_update_config_with_options_list():
    options = [{"network": "patched_network"}, {"web": {"dev_mode": False}}]
    data = build_config("config/basic", None, options=options)
    assert not data.web_dev_mode
    assert data.network == "patched_network"


def test_update_config_with_options_dict():
    options = {"network": "patched_network"}
    data = build_config("config/basic", None, options=options)
    assert data.web_dev_mode
    assert data.network == "patched_network"


def test_web_url_is_read_from_config():
    data = build_config("config/basic")
    assert data.web_url == "https://localhost"


def test_web_url_default_depends_on_proxy():
    options = {"web": {"url": None}}
    data = build_config("config/basic", options=options)
    assert data.web_url == "https://localhost:443"
    data = build_config("config/noproxy", options=options)
    assert data.web_url == "http://localhost:8888"


def test_web_url_required_if_not_proxied():
    with pytest.raises(Exception,
                       match="web_url must be provided"):
        options = {"web": {"url": None, "dev_mode": False}}
        build_config("config/noproxy", options=options)


def read_file(path):
    with open(path, "r") as f:
        return f.read()
