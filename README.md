## OrderlyWeb (Deploy)

This is the deploy scripts for OrderlyWeb.  They are the only part of the system that runs directly on metal.
I am not good at python packaging so some documentation for help me.  These might not be the best ways to do things but they seem to work:

## Installation

From local sources

```
python3 setup.py install --user
```

This installs the package `orderly_web` for programmatic use, and a cli tool `orderly-web` for interacting with the package:

## Usage

```
$ orderly-web --help
Usage:
  orderly_web deploy <path>
  orderly_web status <path>
  orderly_web stop <path> [--volumes] [--network]

Options:
  --volumes   Remove volumes (WARNING: irrevrsible data loss)
  --network   Remove network
```

Here `<path>` is the path to a directory that contains a configuration file `orderly-web.yml` (more options will follow in future versions).
