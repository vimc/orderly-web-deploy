import io
from contextlib import redirect_stdout
import urllib
import time
import json
import ssl
import vault_dev


import orderly_web
from orderly_web.docker_helpers import docker_client, exec_safely


def test_status_when_not_running():
    cfg = orderly_web.read_config("config/complete")
    st = orderly_web.status(cfg)
    assert st.containers["orderly"]["status"] == "missing"
    assert st.containers["web"]["status"] == "missing"
    assert st.volumes["orderly"]["status"] == "missing"
    assert st.network["status"] == "down"


def test_status_representation_is_str():
    cfg = orderly_web.read_config("config/complete")
    st = orderly_web.status(cfg)
    f = io.StringIO()
    with redirect_stdout(f):
        print(st)
    out = f.getvalue()
    assert str(st).strip() == out.strip()
    # __repr__ is called when the object is printed
    assert st.__repr__() == str(st)


def test_start_and_stop():
    cfg = orderly_web.read_config("config/complete")
    try:
        res = orderly_web.start(cfg)
        assert res
        st = orderly_web.status(cfg)
        assert st.containers["orderly"]["status"] == "running"
        assert st.containers["web"]["status"] == "running"
        assert st.volumes["orderly"]["status"] == "created"
        assert st.network["status"] == "up"

        f = io.StringIO()
        with redirect_stdout(f):
            res = orderly_web.start(cfg)
            msg = f.getvalue().strip()
        assert not res
        assert msg.endswith("please run orderly-web stop")

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
        orderly_web.stop(cfg, kill=True, volumes=True, network=True)
        st = orderly_web.status(cfg)
        assert st.containers["orderly"]["status"] == "missing"
        assert st.containers["web"]["status"] == "missing"
        assert st.containers["proxy"]["status"] == "missing"
        assert st.volumes["orderly"]["status"] == "missing"
        assert st.network["status"] == "down"
    finally:
        orderly_web.stop(cfg, kill=True, volumes=True, network=True)


def test_no_devmode_no_ports():
    cfg = orderly_web.read_config("config/noproxy")
    cfg.web_dev_mode = False
    try:
        orderly_web.start(cfg)
        web = cfg.get_container("web")
        assert web.attrs["HostConfig"]["PortBindings"] is None
    finally:
        orderly_web.stop(cfg, kill=True, volumes=True, network=True)


def test_can_pull_on_deploy():
    cfg = orderly_web.read_config("config/noproxy")
    with docker_client() as cl:
        try:
            cl.images.remove(str(cfg.images["migrate"]), noprune=True)
        except docker.errors.ImageNotFound:
            pass
        res = orderly_web.start(cfg, True)
        img = cl.images.get(str(cfg.images["migrate"]))
        assert str(cfg.images["migrate"]) in img.tags
        orderly_web.stop(cfg, kill=True, volumes=True, network=True)


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

        # When reading the configuration we have to interpolate in the
        # correct values here for the vault connection
        cfg = orderly_web.read_config("config/vault")
        cfg.vault.url = "http://localhost:{}".format(s.port)
        cfg.vault.auth_args["token"] = s.token
        res = orderly_web.start(cfg)
        dat = json.loads(http_get("https://localhost/api/v1"))
        assert dat["status"] == "success"

        container = cfg.get_container("orderly")
        res = container.exec_run(["cat", "orderly_envir.yml"])
        assert "ORDERLY_DB_PASS: s3cret" in res[1].decode("UTF-8")

        orderly_web.stop(cfg, kill=True, volumes=True, network=True)


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
