import pytest
import vault_dev

from orderly_web.config import config_string, config_integer, config_boolean, \
    config_image_reference, read_config, DockerImageReference, \
    combine, combine2

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
    cfg = read_config("config/basic")
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

    assert cfg.proxy_enabled
    assert cfg.proxy_ssl_self_signed
    assert str(cfg.images["proxy"]) == "vimc/orderly-web-proxy:mrc-211"


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
    cfg = read_config("config/noproxy")
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
        cfg = read_config("config/complete")
        cfg.vault.url = "http://localhost:{}".format(s.port)
        cfg.vault.auth_args["token"] = s.token

        cfg.resolve_secrets()
        assert not cfg.proxy_ssl_self_signed
        assert cfg.proxy_ssl_certificate == cert
        assert cfg.proxy_ssl_key == key
        assert cfg.orderly_env["ORDERLY_DB_PASS"] == "s3cret"


def test_combine2():
    assert combine2({"a": 1}, {"b": 2}) == \
        {"a": 1, "b": 2}
    assert combine2({"a": {"x": 1}, "b": 2}, {"a": {"x": 3}}) == \
        {"a": {"x": 3}, "b": 2}
    assert combine2({"a": {"x": 1, "y": 4}, "b": 2}, {"a": {"x": 3}}) == \
        {"a": {"x": 3, "y": 4}, "b": 2}
    assert combine2({"a": None, "b": 2}, {"a": {"x": 3}}) == \
        {"a": {"x": 3}, "b": 2}


def test_combine():
    assert combine({"a": 1, "b": 1, "c": 1}, {"a": 2, "b": 2}, {"a": 3}) == \
        {"a": 3, "b": 2, "c": 1}



def read_file(path):
    with open(path, "r") as f:
        return f.read()
