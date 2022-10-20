from orderly_web.config import fetch_config
from orderly_web.constellation import orderly_constellation


def status(path):
    cfg = fetch_config(path)
    obj = orderly_constellation(cfg)
    obj.status()
