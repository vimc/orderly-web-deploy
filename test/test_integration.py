from unittest import TestCase
import io
from contextlib import redirect_stdout
import urllib
import time
import json

import orderly_web


class TestExample(TestCase):

    def test_status_when_not_running(self):
        cfg = orderly_web.read_config("example")
        st = orderly_web.status(cfg)
        self.assertEqual(st.containers["orderly"]["status"], "missing")
        self.assertEqual(st.containers["web"]["status"], "missing")
        self.assertEqual(st.volumes["orderly"]["status"], "missing")
        self.assertEqual(st.network["status"], "down")

    def test_status_representation_is_str(self):
        cfg = orderly_web.read_config("example")
        st = orderly_web.status(cfg)
        f = io.StringIO()
        with redirect_stdout(f):
            print(st)
        out = f.getvalue()
        self.assertEqual(str(st).strip(), out.strip())
        # __repr__ is called when the object is printed
        self.assertEqual(st.__repr__(), str(st))

    def test_start_and_stop(self):
        cfg = orderly_web.read_config("example")
        try:
            res = orderly_web.start(cfg)
            self.assertTrue(res)
            st = orderly_web.status(cfg)
            self.assertEqual(st.containers["orderly"]["status"], "running")
            self.assertEqual(st.containers["web"]["status"], "running")
            self.assertEqual(st.volumes["orderly"]["status"], "created")
            self.assertEqual(st.network["status"], "up")

            f = io.StringIO()
            with redirect_stdout(f):
                res = orderly_web.start(cfg)
                msg = f.getvalue().strip()
            self.assertFalse(res)
            self.assertTrue(msg.endswith("please run orderly-web stop"))

            web = cfg.get_container("web")
            ports = web.attrs["HostConfig"]["PortBindings"]
            self.assertEqual(list(ports.keys()), ["8888/tcp"])

            dat = json.loads(http_get("http://localhost:8888"))
            self.assertEqual(dat["status"], "success")
            orderly_web.stop(cfg, kill=True, volumes=True, network=True)
            st = orderly_web.status(cfg)
            self.assertEqual(st.containers["orderly"]["status"], "missing")
            self.assertEqual(st.containers["web"]["status"], "missing")
            self.assertEqual(st.volumes["orderly"]["status"], "missing")
            self.assertEqual(st.network["status"], "down")
        finally:
            orderly_web.stop(cfg, kill=True, volumes=True, network=True)

    def test_no_devmode_no_ports(self):
        cfg = orderly_web.read_config("example")
        cfg.web_dev_mode = False
        try:
            orderly_web.start(cfg)
            web = cfg.get_container("web")
            self.assertIsNone(web.attrs["HostConfig"]["PortBindings"])
        finally:
            orderly_web.stop(cfg, kill=True, volumes=True, network=True)


# Because we wait for a go signal to come up, we might not be able to
# make the request right away:
def http_get(url, retries=5, poll=0.5):
    for i in range(retries):
        try:
            r = urllib.request.urlopen(url)
            return r.read().decode("UTF-8")
        except (urllib.error.URLError, ConnectionResetError) as e:
            print("sleeping...")
            time.sleep(poll)
            error = e
    raise error
