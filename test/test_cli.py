import io
from contextlib import redirect_stdout

import orderly_web
import orderly_web.cli


def test_cli_basic_usage():
    path = "config/noproxy"
    orderly_web.cli.main(["start", path])

    f = io.StringIO()
    with redirect_stdout(f):
        orderly_web.cli.main(["status", path])
    out = f.getvalue()

    assert "Network:\n    - orderly_web_network: created" in out
    assert "Volumes:\n    - redis (orderly_web_redis_data): created" in out
    assert "- web (orderly_web_web): running" in out

    stop_args = ["stop", path, "--kill", "--volumes", "--network"]
    orderly_web.cli.main(stop_args)

    f = io.StringIO()
    with redirect_stdout(f):
        orderly_web.cli.main(["status", path])
    out = f.getvalue()

    assert "OrderlyWeb not running from 'config/noproxy'" in out
