"""Usage:
  orderly-web start <path> [--extra=PATH] [--option=OPTION]... [--pull]
  orderly-web status <path>
  orderly-web stop <path> [--volumes] [--network] [--kill]
  orderly-web add-users <email>...
  orderly-web add-groups <name>...
  orderly-web add-members <group> <email>...
  orderly-web grant <group> <permission>...

Options:
  --extra=PATH     Path, relative to <path>, of yml file of additional
                   configuration
  --option=OPTION  Additional configuration options, in the form key=value
                   Use dots in key for hierarchical structure, e.g., a.b=value
                   This argument may be repeated to provide multiple arguments
  --pull           Pull images before starting
  --volumes        Remove volumes (WARNING: irreversible data loss)
  --network        Remove network
  --kill           Kill the containers (faster, but possible db corruption)
"""

import docopt
import yaml

from orderly_web.status import print_status
import orderly_web


def main(argv=None):
    target, args = parse_args(argv)
    target(*args)


def parse_args(argv):
    args = docopt.docopt(__doc__, argv)
    if args["start"]:
        path = args["<path>"]
        extra = args["--extra"]
        options = [string_to_dict(x) for x in args["--option"]]
        pull_images = args["--pull"]
        target = orderly_web.start
        args = (path, extra, options, pull_images)
    elif args["status"]:
        path = args["<path>"]
        target = print_status
        args = (path, )
    elif args["stop"]:
        path = args["<path>"]
        kill = args["--kill"]
        target = orderly_web.stop
        args = (path, kill)
    elif args["add-users"]:
        target = orderly_web.add_users
        args = args["<email>"]
    elif args["add-groups"]:
        target = orderly_web.add_groups
        args = args["<name>"]
    elif args["add-members"]:
        target = orderly_web.add_members
        args = (args["<group>"], args["<email>"])
    elif args["grant"]:
        target = orderly_web.grant
        args = (args["<group>"], args["<permission>"])
    return target, args


def string_to_dict(string):
    """Convert a configuration option a.b.c=x to a dictionary
{"a": {"b": "c": x}}"""
    # Won't deal with dots embedded within quotes but that's ok as
    # that should not be allowed generally.
    try:
        key, value = string.split("=")
    except ValueError:
        msg = "Invalid option '{}', expected option in form key=value".format(
            string)
        raise Exception(msg)
    value = yaml_atom_parse(value)
    for k in reversed(key.split(".")):
        value = {k: value}
    return value


def yaml_atom_parse(x):
    ret = yaml.load(x, Loader=yaml.Loader)
    if type(ret) not in [bool, int, float, str]:
        raise Exception("Invalid value '{}' - expected simple type".format(x))
    return ret
