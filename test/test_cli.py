import io
from contextlib import redirect_stdout

import docker

import orderly_web
import orderly_web.cli
from orderly_web.docker_helpers import docker_client


def test_cli_basic_usage():
    path = "config/noproxy"
    orderly_web.cli.main(["start", path])
    st = orderly_web.status(path)
    assert st.is_running
    assert st.containers["web"]["status"] == "running"

    f = io.StringIO()
    with redirect_stdout(f):
        orderly_web.cli.main(["status", path])
    out = f.getvalue()
    assert str(st).strip() == out.strip()

    stop_args = ["stop", path, "--kill", "--volumes", "--network"]
    orderly_web.cli.main(stop_args)
    st = orderly_web.status(path)
    assert not st.is_running
    assert st.containers["web"]["status"] == "missing"
