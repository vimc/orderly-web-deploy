from orderly_web.config import build_config
from orderly_web.constellation import orderly_constellation


def status(path, extra=None):
    cfg = build_config(path, extra=extra)
    obj = orderly_constellation(cfg)
    obj.status()
