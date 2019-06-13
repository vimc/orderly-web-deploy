import io
from contextlib import redirect_stdout
import urllib
import time
import json
import ssl
from urllib import request

import requests
import vault_dev

from orderly_web.config import fetch_config
from orderly_web.docker_helpers import *
import orderly_web


def test_status_when_not_running():
    st = orderly_web.status("config/basic")
    assert not st.is_running
    assert st.containers["orderly"]["status"] == "missing"
    assert st.containers["web"]["status"] == "missing"
    assert st.volumes == {}
    assert st.network is None


def test_status_representation_is_str():
    st = orderly_web.status("config/basic")
    f = io.StringIO()
    with redirect_stdout(f):
        print(st)
    out = f.getvalue()
    assert str(st).strip() == out.strip()
    # __repr__ is called when the object is printed
    assert st.__repr__() == str(st)


def test_start_and_stop():
    path = "config/basic"
    try:
        res = orderly_web.start(path)
        assert res
        st = orderly_web.status(path)
        assert st.containers["orderly"]["status"] == "running"
        assert st.containers["web"]["status"] == "running"
        assert st.volumes["orderly"] == "orderly_web_volume"
        assert st.network == "orderly_web_network"

        f = io.StringIO()
        with redirect_stdout(f):
            res = orderly_web.start(path)
            msg = f.getvalue().strip()
        assert not res
        assert msg.endswith("please run orderly-web stop")

        cfg = fetch_config(path)
        web = cfg.get_container("web")
        ports = web.attrs["HostConfig"]["PortBindings"]
        assert list(ports.keys()) == ["8888/tcp"]
        dat = json.loads(http_get("http://localhost:8888/api/v1"))
        assert dat["status"] == "success"

        web_config = string_from_container(
            web, "/etc/orderly/web/config.properties")
        assert "app.url=https://localhost" in web_config.split("\n")

        # Trivial check that the proxy container works too:
        proxy = cfg.get_container("proxy")
        ports = proxy.attrs["HostConfig"]["PortBindings"]
        assert set(ports.keys()) == set(["443/tcp", "80/tcp"])
        dat = json.loads(http_get("http://localhost/api/v1"))
        assert dat["status"] == "success"
        dat = json.loads(http_get("https://localhost/api/v1"))
        assert dat["status"] == "success"

        # Bring the whole lot down:
        orderly_web.stop(path, kill=True, volumes=True, network=True)
        st = orderly_web.status(path)
        assert not st.is_running
        assert st.containers["orderly"]["status"] == "missing"
        assert st.containers["web"]["status"] == "missing"
        assert st.volumes == {}
        assert st.network is None
        # really removed?
        with docker_client() as cl:
            assert not network_exists(cl, cfg.network)
            assert not volume_exists(cl, cfg.volumes["orderly"])
            assert not container_exists(cl, cfg.containers["proxy"])
    finally:
        orderly_web.stop(path, kill=True, volumes=True, network=True)


def test_start_with_custom_styles():
    path = "config/customcss"
    try:
        options = {"web": {"url": "http://localhost:8888"}}
        res = orderly_web.start(path, options=options)
        assert res
        st = orderly_web.status(path)
        assert st.containers["orderly"]["status"] == "running"
        assert st.containers["web"]["status"] == "running"
        assert st.volumes["css"] == "orderly_web_css"
        assert st.network == "orderly_web_network"

        cfg = fetch_config(path)

        # check that the style volume is really mounted
        api_client = docker.client.from_env().api
        details = api_client.inspect_container(cfg.containers["web"])
        assert len(details['Mounts']) == 3
        css_volume = [v for v in details['Mounts']
                      if v['Type'] == "volume" and
                      v['Name'] == "orderly_web_css"][0]
        assert css_volume['Name'] == "orderly_web_css"
        assert css_volume['Destination'] == "/static/public"

        # check that the style files have been compiled with the custom vars
        web_container = cfg.get_container("web")
        style = string_from_container(web_container,
                                      "/static/public/css/style.css")
        assert "/* Example custom config */" in style

        # check that the custom logo is mounted and appears on the page
        logo_mount = [v for v in details['Mounts']
                      if v['Type'] == "bind"][0]
        expected_destination = "/static/public/img/logo/my-test-logo.png"
        assert logo_mount['Destination'] == expected_destination
        res = requests.get("http://localhost:8888")
        assert """<img src="/img/logo/my-test-logo.png""" in res.text
        res = requests.get("http://localhost:8888/img/logo/my-test-logo.png")
        assert res.status_code == 200
    finally:
        orderly_web.stop(path, kill=True, volumes=True, network=True)


def test_stop_broken_orderly_web():
    path = "config/breaking"

    start_failed = False
    try:
        orderly_web.start(path)
    except docker.errors.APIError:
        start_failed = True

    assert start_failed

    orderly_web.stop("config/breaking")

    # stop without force should have left containers without throwing
    with docker_client() as cl:
        assert container_exists(cl, "orderly_web_orderly")

    orderly_web.stop(path, force=True, network=True, volumes=True)
    with docker_client() as cl:
        assert not container_exists(cl, "orderly_web_orderly")


def test_stop_broken_orderly_web_with_option():

    path = "config/breaking"
    options = [{"network": "ow_broken_test"}]

    start_failed = False
    try:
        orderly_web.start(path, options=options)
    except docker.errors.APIError:
        start_failed = True

    assert start_failed

    with docker_client() as cl:
        assert container_exists(cl, "orderly_web_orderly")
        assert network_exists(cl, "ow_broken_test")

    orderly_web.stop(path, force=True, network=True, volumes=True, options=options)

    with docker_client() as cl:
        assert not container_exists(cl, "orderly_web_orderly")
        assert not network_exists(cl, "ow_broken_test")


def test_stop_broken_orderly_web_with_extra():

    path = "config/breaking"
    extra = "extra"  # defines network as "ow_broken_extra_test"

    start_failed = False
    try:
        orderly_web.start(path, extra=extra)
    except docker.errors.APIError:
        start_failed = True

    assert start_failed

    with docker_client() as cl:
        assert container_exists(cl, "orderly_web_orderly")
        assert network_exists(cl, "ow_broken_extra_test")

    orderly_web.stop(path, force=True, network=True, volumes=True, extra=extra)

    with docker_client() as cl:
        assert not container_exists(cl, "orderly_web_orderly")
        assert not network_exists(cl, "ow_broken_extra_test")


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


def test_vault_ssl():
    with vault_dev.server() as s:
        cl = s.client()
        # Copy the certificates into the vault where we will later on
        # pull from from.
        cert = read_file("proxy/ssl/certificate.pem")
        key = read_file("proxy/ssl/key.pem")
        cl.write("secret/ssl/certificate", value=cert)
        cl.write("secret/ssl/key", value=key)
        cl.write("secret/db/password", value="s3cret")

        path = "config/complete"

        vault_addr = "http://localhost:{}".format(s.port)
        vault_auth = {"args": {"token": s.token}}
        options = {"vault": {"addr": vault_addr, "auth": vault_auth}}

        res = orderly_web.start(path, options=options)
        dat = json.loads(http_get("https://localhost/api/v1"))
        assert dat["status"] == "success"

        cfg = fetch_config(path)
        container = cfg.get_container("orderly")
        res = string_from_container(container, "/orderly/orderly_envir.yml")
        assert "ORDERLY_DB_PASS: s3cret" in res

        orderly_web.stop(path, kill=True, volumes=True, network=True)


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
