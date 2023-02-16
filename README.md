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
  orderly-web stop <path> [--volumes] [--network] [--kill] [--force] [--extra=PATH] [--option=OPTION]...
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
                   signal their running configuration, or if config cannot be parsed.
                   Use with extra and/or option to force stop with configuration options.
```

Here `<path>` is the path to a directory that contains a configuration file `orderly-web.yml` (more options will follow in future versions).

### Examples

To deploy with 2 users:
```
orderly-web start ./config/basic
orderly-web admin ./config/basic add-users test.user@example.com admin.user@example.com
```

To grant the users permissions on an individual basis:
```
orderly-web admin ./config/basic grant test.user@example.com */reports.read
orderly-web admin ./config/basic grant admin.user@example.com */reports.read */reports.review */reports.run
```

Or to add 2 user groups, "funders" and "admin", and grant users permissions via group membership: 
```
orderly-web admin ./config/basic add-groups funders admin
orderly-web admin ./config/basic grant funders */reports.read
orderly-web admin ./config/basic grant admin */reports.read */reports.review */reports.run
orderly-web admin ./config/basic add-members funders test.user@example.com
orderly-web admin ./config/basic add-members admin admin.user@example.com
```

## Development

To test changes during development often the best way is to try and run a deployment. To do this you will need to install the development version of `orderly-web` on a server. The best way to do this is to clone the repo, set the branch to your development branch and follow instructions above for installation.
 
## Testing

Running integration tests requires an environment variable `VAULT_TEST_GITHUB_PAT` to be available. This needs to be a github pat for a user who is a member of the [robots team in the VIMC org](https://github.com/orgs/vimc/teams/robots). This can be read from the vault `vault read secret/vimc-robot/github-pat`. Save it into an environment variable through e.g. your `~/.bashrc` file so it is available to the tests.

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

Configuration is a work in progress and will change as the tool progresses.  See [`config/complete/orderly-web.yml`] for an annotated configuration that covers all the options.

### Modified versions of configurations

It is possible to create sub-configurations that adapt a configuration.  To do this, create a base configuration with shared options and save that as `orderly-web.yml`.  Then, within the same directory, create secondary yml files (named however you want) that override options.  For example if you have an `orderly-web.yml` that contains

```yaml
web:
  port: 443
  name: OrderlyWeb
  dev_mode: false
```

(among other options), you could create a yaml file called `testing.yml` (in the same directory) that contains

```yaml
web:
  port: 8000
  dev_mode: true
```

When run with

```
orderly-web path --extra testing.yml
```

the options in `testing.yml` will override the base configuration.  The options that are not mentioned in the `testing.yml` are left unmodified (i.e, in this case we end up with

```yaml
web:
  port: 8000
  name: OrderlyWeb
  dev_mode: true
```

It is also possible to change options by passing individual changes through with the `--option` flag, for example:

```
orderly-web path --option web.port=8000 --option web.dev_mode=true
```

Use `.` to indicate a level of nesting and do not use spaces around the `=`; the right-hand-side is parsed as if it was yaml.
