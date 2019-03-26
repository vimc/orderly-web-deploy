from unittest import TestCase
import io
from contextlib import redirect_stdout

import orderly_web
import orderly_web.cli

class TestCli(TestCase):
    def test_cli_basic_usage(self):
        path = "example"
        cfg = orderly_web.read_config(path)
        orderly_web.cli.main(["start", path])
        st = orderly_web.status(cfg)
        self.assertEqual(st.containers["web"]["status"], "running")

        f = io.StringIO()
        with redirect_stdout(f):
            orderly_web.cli.main(["status", path])
        out = f.getvalue()
        self.assertEqual(str(st).strip(), out.strip())

        orderly_web.cli.main(["stop", path, "--kill", "--volumes", "--network"])
        st = orderly_web.status(cfg)
        self.assertEqual(st.containers["web"]["status"], "missing")
