import io
from contextlib import redirect_stdout

import docker

import orderly_web
import orderly_web.cli
from orderly_web.docker_helpers import docker_client

def test_cli_basic_usage():
    path = "config/noproxy"
    cfg = orderly_web.read_config(path)
    orderly_web.cli.main(["start", path])
    st = orderly_web.status(cfg)
    assert st.containers["web"]["status"] == "running"

    f = io.StringIO()
    with redirect_stdout(f):
        orderly_web.cli.main(["status", path])
    out = f.getvalue()
    assert str(st).strip() == out.strip()

    stop_args = ["stop", path, "--kill", "--volumes", "--network"]
    orderly_web.cli.main(stop_args)
    st = orderly_web.status(cfg)
    assert st.containers["web"]["status"] == "missing"


def test_cli_pull():
    path = "config/complete"
    cfg = orderly_web.read_config(path)
    with docker_client() as cl:
        try:
            cl.images.remove(str(cfg.images["proxy"]), noprune=True)
        except docker.errors.ImageNotFound:
            pass
        args = ["pull", path]
        orderly_web.cli.main(args)
        img = cl.images.get(str(cfg.images["proxy"]))
        assert str(cfg.images["proxy"]) in img.tags
