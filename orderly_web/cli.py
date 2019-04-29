"""Usage:
  orderly-web start <path> [--pull]
  orderly-web status <path>
  orderly-web stop <path> [--volumes] [--network] [--kill]

Options:
  --pull      Pull images before starting
  --volumes   Remove volumes (WARNING: irreversible data loss)
  --network   Remove network
  --kill      Kill the containers (faster, but possible db corruption)
"""

import docopt

import orderly_web


def main(argv=None):
    args = docopt.docopt(__doc__, argv)
    path = args["<path>"]

    if args["start"]:
        pull_images = args["--pull"]
        orderly_web.start(path, pull_images)
    elif args["status"]:
        print(orderly_web.status(path))
    elif args["stop"]:
        network = args["--network"]
        volumes = args["--volumes"]
        kill = args["--kill"]
        orderly_web.stop(path, network=network, volumes=volumes, kill=kill)
