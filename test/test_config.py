import io
from contextlib import redirect_stdout
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


def test_config_dict_returns_dict():
    assert config_dict(sample_data, ["b"]) == sample_data["b"]


def test_config_dict_strict_returns_dict():
    assert config_dict_strict(sample_data, ["b"], ["x"]) == sample_data["b"]


def test_config_dict_strict_raises_if_keys_missing():
    with pytest.raises(ValueError, match="Expected keys x, y for b"):
        config_dict_strict(sample_data, ["b"], ["x", "y"])


def test_config_dict_strict_raises_if_not_strings():
    dat = {"a": {"b": {"c": 1}}}
    with pytest.raises(ValueError, match="Expected a string for a:b:c"):
        config_dict_strict(dat, ["a", "b"], "c")


def test_config_enum_returns_string():
    assert config_enum(sample_data, ["b", "x"], ["value1", "value2"]) == \
        "value2"


def test_config_enum_raises_if_invalid():
    with pytest.raises(ValueError,
                       match=r"Expected one of \[enum1, enum2\] for b:x"):
        config_enum(sample_data, ["b", "x"], ["enum1", "enum2"])


def test_example_config():
    cfg = build_config("config/basic")
    assert cfg.network == "orderly_web_network"
    assert cfg.volumes["orderly"] == "orderly_web_volume"
    assert cfg.volumes["redis"] == "orderly_web_redis_data"
    assert cfg.containers["redis"] == "orderly_web_redis"
    assert cfg.containers["orderly"] == "orderly_web_orderly"
    assert cfg.containers["web"] == "orderly_web_web"

    assert len(cfg.container_groups) == 1
    assert "orderly_worker" in cfg.container_groups
    assert cfg.container_groups["orderly_worker"]["name"] ==\
        "orderly_web_orderly_worker"
    assert cfg.container_groups["orderly_worker"]["scale"] == 1

    assert cfg.images["redis"].name == "redis"
    assert cfg.images["redis"].tag == "5.0"
    assert str(cfg.images["redis"]) == "redis:5.0"
    assert cfg.images["orderly"].repo == "vimc"
    assert cfg.images["orderly"].name == "orderly.server"
    assert cfg.images["orderly"].tag == "master"
    assert str(cfg.images["orderly"]) == "vimc/orderly.server:master"
    assert cfg.images["orderly_worker"].repo == "vimc"
    assert cfg.images["orderly_worker"].name == "orderly.server"
    assert cfg.images["orderly_worker"].tag == "master"
    assert str(cfg.images["orderly_worker"]) == \
        "vimc/orderly.server:master"
    assert cfg.web_dev_mode
    assert cfg.web_port == 8888
    assert cfg.web_name == "OrderlyWeb"
    assert cfg.web_email == "admin@example.com"
    assert not cfg.web_auth_montagu
    assert cfg.web_auth_fine_grained
    assert cfg.web_auth_github_org == "vimc"
    assert cfg.web_auth_github_team == ""
    assert cfg.web_auth_github_app["id"] == "notarealid"
    assert cfg.web_auth_github_app["secret"] == "notarealsecret"
    assert cfg.sass_variables is None
    assert "css-generator" not in cfg.images
    assert "css" not in cfg.volumes
    assert cfg.logo_name is None
    assert cfg.logo_path is None
    assert cfg.favicon_path is None

    assert cfg.proxy_enabled
    assert cfg.proxy_ssl_self_signed
    assert str(cfg.images["proxy"]) == "vimc/orderly-web-proxy:master"

    assert cfg.orderly_initial_source == "clone"
    assert cfg.orderly_initial_url == \
        "https://github.com/reside-ic/orderly-example"

    assert cfg.slack_webhook_url == \
        "https://hooks.slack.com/services/T000/B000/XXXX"


def test_documents_volume_inclusion():
    cfg = build_config("config/basic")
    assert "documents" in cfg.volumes
    cfg = build_config("config/customcss")
    assert "documents" not in cfg.volumes


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
    expected_icon_path = os.path.abspath(
        os.path.join(cfg.path, "my-test-favicon.png"))
    assert cfg.favicon_path == expected_icon_path


def test_config_montagu():
    path = "config/montagu"
    cfg = build_config(path)
    assert cfg.montagu_url == "http://montagu"
    assert cfg.montagu_api_url == "http://montagu/api"


def test_default_workers():
    path = "config/montagu"
    cfg = build_config(path)
    assert len(cfg.container_groups) == 1
    assert "orderly_worker" in cfg.container_groups
    assert cfg.container_groups["orderly_worker"]["name"] ==\
        "orderly_web_orderly_worker"
    assert cfg.container_groups["orderly_worker"]["scale"] == 1


def test_string_representation():
    img = DockerImageReference("a", "b", "c")
    assert str(img) == "a/b:c"


def test_config_image_reference():
    data = {"foo": {
        "repo": "a", "name": "b", "tag": "c", "other": "d", "num": 1},
        "bar": {
        "name": "e", "tag": "f"
    }}
    assert str(config_image_reference(data, "foo")) == "a/b:c"
    assert str(config_image_reference(data, ["foo"], "other")) == "a/d:c"
    assert str(config_image_reference(data, "bar")) == "e:f"
    with pytest.raises(KeyError):
        config_image_reference(data, ["foo"], "missing")
    with pytest.raises(ValueError):
        config_image_reference(data, ["foo"], "num")


def test_config_no_proxy():
    cfg = build_config("config/noproxy")
    assert not cfg.proxy_enabled


def test_config_proxy_not_enabled():
    options = {"proxy": {"enabled": False}}
    cfg = build_config("config/noproxy", options=options)
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
        cl.write("secret/github/id", value="ghkey")
        cl.write("secret/github/secret", value="ghs3cret")
        cl.write("secret/ssh", public="public-key-data",
                 private="private-key-data")
        cl.write("secret/slack/webhook", value="http://webhook")

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
        assert cfg.web_auth_github_app["id"] == "ghkey"
        assert cfg.web_auth_github_app["secret"] == "ghs3cret"
        assert cfg.orderly_ssh["private"] == "private-key-data"
        assert cfg.orderly_ssh["public"] == "public-key-data"


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


def combine_can_replace_dict():
    base = {"a": {"c": {"d": "x"}}, "b": "y"}
    options = {"a": {"c": None}}
    combine(base, options)
    assert base["a"]["c"] is None


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


def test_github_app_not_needed_if_using_montagu():
    options = {"web": {"auth": {"montagu": True,
                                "montagu_url": "whatever",
                                "montagu_api_url": "whatever"}}}
    data = build_config("config/basic", options=options)
    assert data.web_auth_github_app is None


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


def test_github_auth_required_if_not_using_montagu():
    with pytest.raises(KeyError, match="web:auth:github_org"):
        options = {"web": {"auth": {"github_org": None}}}
        cfg = build_config("config/basic", options=options)


def test_github_auth_ignored_if_using_montagu():
    options = {"web": {"auth": {"montagu": True,
                                "montagu_url": "https://localhost",
                                "montagu_api_url": "https://localhost"}}}
    cfg = build_config("config/basic", options=options)
    assert cfg.web_auth_github_app is None
    assert cfg.web_auth_github_org is None
    assert cfg.web_auth_github_team is None


def test_can_use_url_for_initial_source():
    url = "https://github.com/reside-ic/orderly-example"
    options = {"orderly": {"initial": {"source": "clone", "url": url}}}
    cfg = build_config("config/basic", options=options)
    assert cfg.orderly_initial_source == "clone"
    assert cfg.orderly_initial_url == url


def test_initial_clone_requires_url():
    options = {"orderly": {"initial": {"source": "clone"}}}
    with pytest.raises(KeyError, match="orderly:initial:url"):
        cfg = build_config("config/montagu", options=options)


def test_initial_demo_ignores_url():
    url = "https://github.com/reside-ic/orderly-example"
    options = {"orderly": {"initial": {"source": "demo", "url": url}}}
    f = io.StringIO()
    with redirect_stdout(f):
        cfg = build_config("config/basic", options=options)
    out = f.getvalue()
    assert "NOTE: Ignoring orderly:initial:url" in out


def test_multiple_workers_config():
    options = {"orderly": {"workers": 2}}
    cfg = build_config("config/basic", options=options)

    assert len(cfg.container_groups) == 1
    assert "orderly_worker" in cfg.container_groups
    assert cfg.container_groups["orderly_worker"]["name"] ==\
        "orderly_web_orderly_worker"
    assert cfg.container_groups["orderly_worker"]["scale"] == 2


def read_file(path):
    with open(path, "r") as f:
        return f.read()
