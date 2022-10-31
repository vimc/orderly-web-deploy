from constellation.notifier import Notifier

from orderly_web.config import build_config
from orderly_web.constellation import orderly_constellation
from orderly_web.pull import pull


def start(path, extra=None, options=None, pull_images=False):
    cfg = build_config(path, extra, options)
    cfg.resolve_secrets()
    obj = orderly_constellation(cfg)
    if pull_images:
        # Manually pull images which are not part of the constellation
        pull(cfg.non_constellation_images)

    notifier = Notifier(cfg.slack_webhook_url)
    notifier.post("*Starting* deploy to {}".format(cfg.web_url))
    try:
        obj.start(pull_images=pull_images)
        notifier.post("*Completed* deploy to {} :shipit:"
                      .format(cfg.web_url))
        config_save(cfg)
        return True
    except Exception:
        notifier.post("*Failed* deploy to {} :bomb:".format(cfg.web_url))
        raise


def config_save(cfg):
    print("Persisting configuration")
    cfg.save()
