import importlib
from unittest.mock import patch
import pytest

from orderly_web.stop import stop
from orderly_web.config import build_config


# helper from https://stackoverflow.com/questions/52324568/
# how-to-mock-a-function-called-in-a-function-inside-a-module-
# with-the-same-name
def module_patch(*args):
    target = args[0]
    components = target.split('.')
    for i in range(len(components), 0, -1):
        try:
            # attempt to import the module
            imported = importlib.import_module('.'.join(components[:i]))

            # module was imported, let's use it in the patch
            mock = patch(*args)
            mock.getter = lambda: imported
            mock.attribute = '.'.join(components[i:])
            return mock
        except Exception as exc:
            pass

    # did not find a module, just return the default mock
    return patch(*args)


def test_stop_fails_if_constellation_errors():
    with module_patch("orderly_web.stop.fetch_config") as fetch_config:
        cfg = build_config("config/basic")
        del cfg.outpack_enabled
        fetch_config.return_value = cfg
        msg = "Unable to manage constellation from existing config."
        with pytest.raises(Exception, match=msg):
            stop("config/basic")


def test_stop_succeeds_if_forced():
    with module_patch("orderly_web.stop.fetch_config") as fetch_config:
        cfg = build_config("config/basic")
        del cfg.outpack_enabled
        fetch_config.return_value = cfg
        stop("config/basic", force=True)
