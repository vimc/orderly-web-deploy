"""Usage:
  orderly-web start <path>
  orderly-web status <path>
  orderly-web stop <path> [--volumes] [--network] [--kill]

Options:
  --volumes   Remove volumes (WARNING: irreversible data loss)
  --network   Remove network
  --kill      Kill the containers (faster, but possible db corruption)
"""

import docopt

import orderly_web


def main(argv=None):
    args = docopt.docopt(__doc__, argv)
    path = args["<path>"]

    cfg = orderly_web.read_config(path)
    if args["start"]:
        orderly_web.start(cfg)
    elif args["status"]:
        print(orderly_web.status(cfg))
    elif args["stop"]:
        network = args["--network"]
        volumes = args["--volumes"]
        kill = args["--kill"]
        orderly_web.stop(cfg, network=network, volumes=volumes, kill=kill)
