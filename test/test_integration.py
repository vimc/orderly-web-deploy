import io
import os
from contextlib import redirect_stdout
import pytest
import urllib
import time
import json
import ssl
import re
import docker
from unittest import mock
from urllib import request
from unittest.mock import patch, call

import requests
import vault_dev

import constellation.docker_util as docker_util
from constellation.notifier import Notifier

from orderly_web.config import fetch_config, build_config
from orderly_web.docker_helpers import docker_client
from orderly_web.errors import OrderlyWebConfigError
import orderly_web


def test_start_and_stop():
    path = "config/basic"
    try:
        res = orderly_web.start(path)
        assert res

        cl = docker.client.from_env()
        containers = cl.containers.list()
        assert len(containers) == 5
        cfg = fetch_config(path)
        assert docker_util.network_exists(cfg.network)
        assert docker_util.volume_exists(cfg.volumes["orderly"])
        assert docker_util.volume_exists(cfg.volumes["documents"])
        assert docker_util.volume_exists(cfg.volumes["redis"])
        assert docker_util.container_exists("orderly_web_web")
        assert docker_util.container_exists("orderly_web_orderly")
        assert docker_util.container_exists("orderly_web_proxy")
        assert docker_util.container_exists("orderly_web_redis")

        names = []
        for container in containers:
            names.append(container.name)
        assert any(re.match(r"orderly_web_orderly_worker_\w+", name)
                   for name in names)

        web = cfg.get_container("web")
        web_config = docker_util.string_from_container(
            web, "/etc/orderly/web/config.properties").split("\n")

        assert "app.url=https://localhost" in web_config
        assert "auth.github_key=notarealid" in web_config
        assert "auth.github_secret=notarealsecret" in web_config
        assert "orderly.server=http://orderly_web_orderly:8321" in web_config

        # Trivial check that the proxy container works too:
        proxy = cfg.get_container("proxy")
        ports = proxy.attrs["HostConfig"]["PortBindings"]
        assert set(ports.keys()) == set(["443/tcp", "80/tcp"])
        dat = json.loads(http_get("http://localhost/api/v1"))
        assert dat["status"] == "success"
        dat = json.loads(http_get("https://localhost/api/v1"))
        assert dat["status"] == "success"

        # Orderly volume contains only the stripped down example from
        # the URL, not the whole demo:
        orderly = cfg.get_container("orderly")
        src = docker_util.exec_safely(orderly, ["ls", "/orderly/src"])[1]
        src_contents = src.decode("UTF-8").strip().split("\n")
        assert set(src_contents) == set(["README.md", "example"])

        # Bring the whole lot down:
        orderly_web.stop(path, kill=True, volumes=True, network=True)
        containers = cl.containers.list()
        assert len(containers) == 0
        assert not docker_util.network_exists(cfg.network)
        assert not docker_util.volume_exists(cfg.volumes["orderly"])
        assert not docker_util.volume_exists(cfg.volumes["documents"])
        assert not docker_util.volume_exists(cfg.volumes["redis"])
        assert not docker_util.container_exists("orderly_web_web")
        assert not docker_util.container_exists("orderly_web_orderly")
        assert not docker_util.container_exists("orderly_web_proxy")
        assert not docker_util.container_exists("orderly_web_redis")
    finally:
        orderly_web.stop(path, kill=True, volumes=True, network=True)


def test_start_with_custom_styles():
    path = "config/customcss"
    try:
        options = {"web": {"url": "http://localhost:8888"}}
        res = orderly_web.start(path, options=options)
        assert res

        cfg = fetch_config(path)

        assert docker_util.network_exists(cfg.network)
        assert docker_util.volume_exists(cfg.volumes["css"])
        assert docker_util.container_exists("orderly_web_web")
        assert docker_util.container_exists("orderly_web_orderly")
        assert not docker_util.volume_exists("documents")

        # check that the style volume is really mounted
        cl = docker.client.from_env()
        api_client = cl.api
        details = api_client.inspect_container("orderly_web_web")
        assert len(details['Mounts']) == 2
        css_volume = [v for v in details['Mounts']
                      if v['Type'] == "volume" and
                      v['Name'] == "orderly_web_css"][0]
        assert css_volume['Name'] == "orderly_web_css"
        assert css_volume['Destination'] == "/static/public/css"

        # check that the style files have been compiled with the custom vars
        web_container = cfg.get_container("web")
        style = docker_util.string_from_container(
            web_container, "/static/public/css/style.css")
        assert "/* Example custom config */" in style

        # check that js files are there also
        res = requests.get("http://localhost:8888/js/index.bundle.js")
        assert res.status_code == 200

        # check that the custom logo exists in container and appears
        # on the page
        web = cfg.get_container("web")
        expected_destination = "/static/public/img/logo/my-test-logo.png"
        logo = docker_util.bytes_from_container(web, expected_destination)
        assert len(logo) > 0
        res = requests.get("http://localhost:8888")
        assert """<img src="http://localhost:8888/img/logo/my-test-logo.png"""\
               in res.text
        res = requests.get("http://localhost:8888/img/logo/my-test-logo.png")
        assert res.status_code == 200
    finally:
        orderly_web.stop(path, kill=True, volumes=True, network=True)


def test_stop_broken_orderly_web():
    path = "config/breaking"
    try:
        start_failed = False
        try:
            orderly_web.start(path)
        except docker.errors.APIError:
            start_failed = True

        assert start_failed

        stop_failed = False
        try:
            orderly_web.stop("config/breaking")
        except OrderlyWebConfigError:
            stop_failed = True

        assert stop_failed

        assert docker_util.container_exists("orderly_web_orderly")
    finally:
        orderly_web.stop(path, force=True, network=True, volumes=True)
        assert not docker_util.container_exists("orderly_web_orderly")


def test_stop_broken_orderly_web_with_option():
    path = "config/breaking"
    options = [{"network": "ow_broken_test"}]
    try:
        start_failed = False
        try:
            orderly_web.start(path, options=options)
        except docker.errors.APIError:
            start_failed = True

        assert start_failed

        assert docker_util.container_exists("orderly_web_orderly")
        assert docker_util.network_exists("ow_broken_test")

    finally:
        orderly_web.stop(path, force=True, network=True, volumes=True,
                         options=options)
    assert not docker_util.container_exists("orderly_web_orderly")
    assert not docker_util.network_exists("ow_broken_test")


def test_stop_broken_orderly_web_with_extra():
    path = "config/breaking"
    extra = "extra"  # defines network as "ow_broken_extra_test"
    try:
        start_failed = False
        try:
            orderly_web.start(path, extra=extra)
        except docker.errors.APIError:
            start_failed = True

        assert start_failed
        assert docker_util.container_exists("orderly_web_orderly")
        assert docker_util.network_exists("ow_broken_extra_test")
    finally:
        orderly_web.stop(path, force=True, network=True, volumes=True,
                         extra=extra)
        assert not docker_util.container_exists("orderly_web_orderly")
        assert not docker_util.network_exists("ow_broken_extra_test")


def test_start_with_montagu_config():
    path = "config/montagu"
    try:
        res = orderly_web.start(path)
        assert res

        cfg = fetch_config(path)

        assert docker_util.network_exists(cfg.network)
        assert docker_util.container_exists("orderly_web_web")
        assert docker_util.container_exists("orderly_web_orderly")

        web = cfg.get_container("web")
        web_config = docker_util.string_from_container(
            web, "/etc/orderly/web/config.properties").split("\n")

        assert "montagu.url=http://montagu" in web_config
        assert "montagu.api_url=http://montagu/api" in web_config
        assert 'auth.github_org=' in web_config
        assert 'auth.github_team=' in web_config

    finally:
        orderly_web.stop(path, kill=True, volumes=True, network=True)


def test_admin_cli():
    path = "config/basic"
    try:
        orderly_web.start(path)
        result = orderly_web.add_users(path, ["test.user@gmail.com"])
        expected = "Saved user with email 'test.user@gmail.com' to the " \
                   "database"
        assert expected in result
        result = orderly_web.add_groups(path, ["funders"])
        assert "Saved user group 'funders' to the database" in result
        result = orderly_web.add_members(path, "funders",
                                         ["test.user@gmail.com"])
        expected = "Added user with email 'test.user@gmail.com' to user " \
                   "group 'funders'"
        assert expected in result
        result = orderly_web.grant(path, "funders", ["*/reports.read"])
        expected = "Gave user group 'funders' the permission '*/reports.read'"
        assert expected in result
        result = orderly_web.grant(path, "funders", ["*/nonsense"])
        assert "Unknown permission : 'nonsense'" in result
    finally:
        orderly_web.stop(path, kill=True, volumes=True, network=True)


def test_no_devmode_no_ports():
    path = "config/noproxy"
    options = {"web": {"dev_mode": False,
                       "url": "http://localhost"}}

    try:
        orderly_web.start(path, options=options)
        cfg = fetch_config(path)
        assert not cfg.web_dev_mode
        web = cfg.get_container("web")
        assert web.attrs["HostConfig"]["PortBindings"] is None
    finally:
        orderly_web.stop(path, kill=True, volumes=True, network=True)


def test_can_pull_on_deploy():
    path = "config/noproxy"
    migrate_image = orderly_web.config.build_config(path).images["migrate"]
    with docker_client() as cl:
        try:
            cl.images.remove(str(migrate_image), noprune=True)
        except docker.errors.ImageNotFound:
            pass
        res = orderly_web.start(path, pull_images=True)
        img = cl.images.get(str(migrate_image))
        assert str(migrate_image) in img.tags
        orderly_web.stop(path, kill=True, volumes=True, network=True)


def test_without_github_app_for_montagu():
    path = "config/basic"
    options = {"web": {"auth": {"montagu": True,
                                "montagu_url": "montagu",
                                "montagu_api_url": "montagu/api",
                                "github_key": None,
                                "github_secret": None}}}
    res = orderly_web.start(path, options=options)
    assert res
    cfg = fetch_config(path)
    assert docker_util.network_exists(cfg.network)
    assert docker_util.container_exists("orderly_web_web")
    assert docker_util.container_exists("orderly_web_orderly")

    orderly_web.stop(path, kill=True, volumes=True, network=True)


# To run this test you will need a token for the vimc robot user -
# this can be found in the montagu vault as
# /secret/vimc-robot/vault-token
# This environment variable is configured on travis
def test_vault_github_login_with_prompt():
    if "VAULT_AUTH_GITHUB_TOKEN" in os.environ:
        del os.environ["VAULT_AUTH_GITHUB_TOKEN"]
    with mock.patch('builtins.input',
                    return_value=os.environ["VAULT_TEST_GITHUB_PAT"]):
        with vault_dev.server() as s:
            cl = s.client()
            enable_github_login(cl)
            cl.write("secret/db/password", value="s3cret")

            path = "config/vault"
            vault_addr = "http://localhost:{}".format(s.port)
            options = {"vault": {"addr": vault_addr}}

            orderly_web.start(path, options=options)

            cfg = fetch_config(path)
            container = cfg.get_container("orderly")
            res = docker_util.string_from_container(container,
                                                    "/root/.Renviron")
            assert "ORDERLY_DB_PASS=s3cret" in res

            orderly_web.stop(path, kill=True, volumes=True, network=True)


# To run this test you will need a token for the vimc robot user -
# this can be found in the montagu vault as
# /secret/vimc-robot/vault-token
# This environment variable is configured on travis
def test_vault_github_login_from_env():
    os.environ["VAULT_AUTH_GITHUB_TOKEN"] = os.environ["VAULT_TEST_GITHUB_PAT"]
    with vault_dev.server() as s:
        cl = s.client()
        enable_github_login(cl)
        cl.write("secret/db/password", value="s3cret")

        path = "config/vault"
        vault_addr = "http://localhost:{}".format(s.port)
        options = {"vault": {"addr": vault_addr}}

        orderly_web.start(path, options=options)

        cfg = fetch_config(path)
        container = cfg.get_container("orderly")
        res = docker_util.string_from_container(container,
                                                "/root/.Renviron")
        assert "ORDERLY_DB_PASS=s3cret" in res

        orderly_web.stop(path, kill=True, volumes=True,
                         network=True)


# To run this test you will need a token for the vimc robot user -
# this can be found in the montagu vault as
# /secret/vimc-robot/vault-token
# This environment variable is configured on travis
def test_vault_github_login_with_mount_path():
    os.environ["VAULT_AUTH_GITHUB_TOKEN"] = os.environ["VAULT_TEST_GITHUB_PAT"]
    with vault_dev.server() as s:
        cl = s.client()
        enable_github_login(cl, path="github-custom")
        cl.write("secret/db/password", value="s3cret")

        path = "config/vault"
        vault_addr = "http://localhost:{}".format(s.port)
        options = {"vault":
                   {"addr": vault_addr,
                    "auth":
                    {"method": "github",
                     "args": {"mount_point": "github-custom"}}}}

        orderly_web.start(path, options=options)

        cfg = fetch_config(path)
        container = cfg.get_container("orderly")
        res = docker_util.string_from_container(container,
                                                "/root/.Renviron")
        assert "ORDERLY_DB_PASS=s3cret" in res

        orderly_web.stop(path, kill=True, volumes=True,
                         network=True)


def test_error_if_orderly_not_initialised():
    path = "config/basic"
    options = {"orderly": {"initial": None}}
    cfg = build_config(path, options=options)
    # ensure this test behaves sensibly if state is a bit messy:
    with docker_client() as cl:
        docker_util.remove_volume(cfg.volumes["orderly"])
    try:
        with pytest.raises(Exception,
                           match="Orderly volume not initialised"):
            res = orderly_web.start(path, options=options)
    finally:
        orderly_web.stop(path, force=True, network=True, volumes=True,
                         kill=True)


def test_can_start_with_prepared_volume():
    path = "config/basic"
    options = {"orderly": {"initial": None}}
    cfg = build_config(path, options=options)

    # ensure this test behaves sensibly if state is a bit messy:
    with docker_client() as cl:
        docker_util.remove_volume(cfg.volumes["orderly"])
        image = str(cfg.images["orderly"])
        mounts = [docker.types.Mount("/orderly", cfg.volumes["orderly"])]
        args = ["Rscript", "-e", "orderly:::create_orderly_demo('/orderly')"]
        cl.containers.run(
            image, entrypoint=args, mounts=mounts, auto_remove=True)

    try:
        f = io.StringIO()
        with redirect_stdout(f):
            res = orderly_web.start(path, options=options)
        assert res
        out = f.getvalue()
        expected = '[orderly] orderly volume already contains data - not '\
            'initialising'
        assert expected in out.splitlines()
    finally:
        orderly_web.stop(path, kill=True, volumes=True, network=True)


def test_notifies_slack_on_success():
    with patch.object(Notifier, 'post',
                      return_value=None) as mock_notify:
        path = "config/basic"
        try:
            orderly_web.start(path)
        finally:
            orderly_web.stop(path, kill=True, volumes=True, network=True)
    calls = [call("*Starting* deploy to https://localhost"),
             call("*Completed* deploy to https://localhost :shipit:")]
    mock_notify.assert_has_calls(calls)


def test_notifies_slack_on_fail():
    with patch.object(Notifier, 'post',
                      return_value=None) as mock_notify:
        path = "config/breaking"
        try:
            orderly_web.start(path)
        except docker.errors.APIError:
            start_failed = True
        finally:
            orderly_web.stop(path, force=True, network=True, volumes=True)
    calls = [call("*Starting* deploy to https://localhost"),
             call("*Failed* deploy to https://localhost :bomb:")]
    mock_notify.assert_has_calls(calls)


def test_start_and_stop_multiple_workers():
    options = {"orderly": {"workers": 2}}
    path = "config/basic"
    try:
        res = orderly_web.start(path, options=options)
        assert res
        assert docker_util.container_exists("orderly_web_web")
        assert docker_util.container_exists("orderly_web_orderly")
        assert docker_util.container_exists("orderly_web_proxy")
        assert docker_util.container_exists("orderly_web_redis")

        cl = docker.client.from_env()
        containers = cl.containers.list()
        assert len(containers) == 6
        names = []
        for container in containers:
            names.append(container.name)
        workers = list(filter(lambda name: re.match(
            r"orderly_web_orderly_worker_\w+", name), names))
        assert len(workers) == 2

        # Bring the whole lot down:
        orderly_web.stop(path, kill=True, volumes=True, network=True)
        containers = cl.containers.list()
        assert len(containers) == 0
    finally:
        orderly_web.stop(path, kill=True, volumes=True, network=True)


def test_wait_for_redis_exists():
    path = "config/basic"
    try:
        res = orderly_web.start(path)
        assert res
        assert docker_util.container_exists("orderly_web_web")
        assert docker_util.container_exists("orderly_web_orderly")
        assert docker_util.container_exists("orderly_web_proxy")
        assert docker_util.container_exists("orderly_web_redis")

        cfg = fetch_config(path)
        container = cfg.get_container("redis")
        res = docker_util.string_from_container(container,
                                                "/wait_for_redis")
        assert re.match(r'#!/usr/bin/env bash', res)
    finally:
        orderly_web.stop(path, kill=True, volumes=True, network=True)


def enable_github_login(cl, path="github"):
    cl.sys.enable_auth_method(method_type="github", path=path)
    policy = """
           path "secret/*" {
             capabilities = ["read", "list"]
           }
           """

    cl.sys.create_or_update_policy(
        name='secret-reader',
        policy=policy,
    )

    cl.auth.github.map_team(
        team_name="robots",
        policies=["secret-reader"],
        mount_point=path
    )

    cl.auth.github.configure(organization="vimc", mount_point=path)


# Because we wait for a go signal to come up, we might not be able to
# make the request right away:
def http_get(url, retries=5, poll=0.5):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    for i in range(retries):
        try:
            r = urllib.request.urlopen(url, context=ctx)
            return r.read().decode("UTF-8")
        except (urllib.error.URLError, ConnectionResetError) as e:
            print("sleeping...")
            time.sleep(poll)
            error = e
    raise error


def read_file(path):
    with open(path, "r") as f:
        return f.read()
