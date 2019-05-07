## OrderlyWeb (Deploy)

[![Build Status](https://travis-ci.org/vimc/orderly-web-deploy.svg?branch=master)](https://travis-ci.org/vimc/orderly-web-deploy)
[![codecov.io](https://codecov.io/github/vimc/orderly-web-deploy/coverage.svg?branch=master)](https://codecov.io/github/vimc/orderly-web-deploy?branch=master)

This is the deploy scripts for OrderlyWeb.  They are the only part of the system that runs directly on metal.
I am not good at python packaging so some documentation for help me.  These might not be the best ways to do things but they seem to work:

## Installation

From local sources

```
python3 setup.py install --user
```

(you may need `--upgrade` to upgrade older versions of python packages).

This installs the package `orderly_web` for programmatic use, and a cli tool `orderly-web` for interacting with the package:

## Usage

```
$ orderly-web --help
Usage:
  orderly-web start <path> [--extra=PATH] [--option=OPTION]... [--pull]
  orderly-web status <path>
  orderly-web stop <path> [--volumes] [--network] [--kill]

Options:
  --extra=PATH     Path, relative to <path>, of yml file of additional
                   configuration
  --option=OPTION  Additional configuration options, in the form key=value
                   Use dots in key for hierarchical structure, e.g., a.b=value
  --pull           Pull images before starting
  --volumes        Remove volumes (WARNING: irreversible data loss)
  --network        Remove network
  --kill           Kill the containers (faster, but possible db corruption)
```

Here `<path>` is the path to a directory that contains a configuration file `orderly-web.yml` (more options will follow in future versions).

## Testing

Run

```
python3 setup.py test
```

This will take a while.  There will be lots of warnings like:

```
ResourceWarning: unclosed <socket.socket fd=8,
```

which are out of our control (see the helper `docker_client` in `docker_helpers.py` for details).

## Configuration

Configuration is a work in progress and will change as the tool progresses.  See [`config/complete/orderly-web.yml`] for an annotated configuration.
