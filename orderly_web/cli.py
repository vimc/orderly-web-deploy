"""Usage:
  orderly-web start <path> [--extra=PATH] [--option=OPTION]... [--pull]
  orderly-web status <path>
  orderly-web stop <path> [--volumes] [--network] [--kill] [--force]
    [--extra=PATH] [--option=OPTION]...
  orderly-web admin <path> add-users <email>...
  orderly-web admin <path> add-groups <name>...
  orderly-web admin <path> add-members <group> <email>...
  orderly-web admin <path> grant <group> <permission>...

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
  --force          Force stop even if containers are corrupted and cannot
                   signal their running configuration, or if config cannot be
                   parsed. Use with extra and/or option to force stop with
                   configuration options.
"""

import docopt
import yaml

import orderly_web


def main(argv=None):
    target, args = parse_args(argv)
    target(*args)


def parse_args(argv):
    args = docopt.docopt(__doc__, argv)
    path = args["<path>"]
    if args["start"]:
        extra = args["--extra"]
        options = parse_option(args)
        pull_images = args["--pull"]
        target = orderly_web.start
        args = (path, extra, options, pull_images)
    elif args["status"]:
        target = orderly_web.status
        args = (path, )
    elif args["stop"]:
        kill = args["--kill"]
        network = args["--network"]
        volumes = args["--volumes"]
        force = args["--force"]
        extra = args["--extra"]
        options = parse_option(args)
        target = orderly_web.stop
        args = (path, kill, network, volumes, force, extra, options)
    elif args["admin"]:
        target, args = parse_admin_args(args)
    return target, args


def parse_option(args):
    return [string_to_dict(x) for x in args["--option"]]


def parse_admin_args(args):
    path = args["<path>"]
    if args["add-users"]:
        target = orderly_web.add_users
        args = (path, args["<email>"])
    elif args["add-groups"]:
        target = orderly_web.add_groups
        args = (path, args["<name>"])
    elif args["add-members"]:
        target = orderly_web.add_members
        args = (path, args["<group>"], args["<email>"])
    elif args["grant"]:
        target = orderly_web.grant
        args = (path, args["<group>"], args["<permission>"])
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
