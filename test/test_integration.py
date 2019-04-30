import io
from contextlib import redirect_stdout
import urllib
import time
import json
import ssl
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
        assert st.volumes["orderly"]["status"] == "created"
        assert st.network["status"] == "up"

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
        assert st.containers["proxy"]["status"] == "missing"
        assert st.volumes == {}
        assert st.network is None
        # really removed?
        with docker_client() as cl:
            assert not network_exists(cl, cfg.network)
            assert not volume_exists(cl, cfg.volumes["orderly"])
    finally:
        orderly_web.stop(path, kill=True, volumes=True, network=True)


def test_no_devmode_no_ports():
    path = "config/noproxy"
    options = {"web": {"dev_mode": False}}

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
    cfg = orderly_web.read_config(path)
    with docker_client() as cl:
        try:
            cl.images.remove(str(cfg.images["migrate"]), noprune=True)
        except docker.errors.ImageNotFound:
            pass
        res = orderly_web.start(path, pull_images=True)
        img = cl.images.get(str(cfg.images["migrate"]))
        assert str(cfg.images["migrate"]) in img.tags
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
