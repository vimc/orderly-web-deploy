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


def test_example_config():
    cfg = build_config("config/basic")
    assert cfg.network == "orderly_web_network"
    assert cfg.volumes["orderly"] == "orderly_web_volume"
    assert cfg.volumes["redis"] == "orderly_web_redis_data"
    assert cfg.container_prefix == "orderly_web"
    assert cfg.containers["redis"] == "redis"
    assert cfg.containers["orderly"] == "orderly"
    assert cfg.containers["orderly_worker"] == "orderly_worker"
    assert cfg.containers["web"] == "web"

    assert cfg.workers == 1
    assert cfg.images["redis"].name == "redis"
    assert cfg.images["redis"].tag == "5.0"
    assert str(cfg.images["redis"]) == "library/redis:5.0"
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
    assert cfg.workers == 1


def test_multiple_workers_config():
    options = {"orderly": {"workers": 2}}
    cfg = build_config("config/basic", options=options)

    assert cfg.workers == 2


def test_config_no_proxy():
    cfg = build_config("config/noproxy")
    assert not cfg.proxy_enabled


def test_config_proxy_not_enabled():
    options = {"proxy": {"enabled": False}}
    cfg = build_config("config/noproxy", options=options)
    assert not cfg.proxy_enabled


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


def read_file(path):
    with open(path, "r") as f:
        return f.read()
