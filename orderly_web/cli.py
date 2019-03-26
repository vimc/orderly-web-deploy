"""orderly_web

Usage:
  orderly_web deploy <path>
  orderly_web status <path>
  orderly_web stop <path> [--volumes] [--network]

Options:
  --volumes   Remove volumes (WARNING: irrevrsible data loss)
  --network   Remove network
"""

import docopt

import orderly_web


def main():
    args = docopt.docopt(__doc__)
    path = args["<path>"]

    cfg = orderly_web.read_config(path)
    if args["deploy"]:
        orderly_web.deploy(cfg)
    elif args["status"]:
        print(orderly_web.status(cfg))
    elif args["stop"]:
        network = args["--network"]
        volumes = args["--volumes"]
        orderly_web.stop(cfg, network=network, volumes=volumes)
