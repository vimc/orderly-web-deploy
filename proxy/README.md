## OrderlyWeb Proxy

A docker-based standalone proxy for use in applications where orderly web is not running under another application (as we do for [montagu](https://github.com/vimc/montagu))

The configuration takes as a starting point [`montagu-proxy`](https://github.com/vimc/montagu-proxy) though our needs are slightly more simple:
  - no metrics endpoint
  - fewer things are proxied

### Configuration

Before starting we need to know what we are proxying (i.e., the name of the `orderly_web` container on the docker network) and what the proxy will be seen as to the outside world (the hostname, and ports for http and https).  The entrypoint takes these four values as arguments.

### SSL Certificates

The server will not start until the files `/run/proxy/certificate.pem` and `/run/proxy/ssl_key.pem` exist - you can get these into the container however you like; the proxy will poll for them and start within a second of them appearing.

### Self signed certificate

For testing it is useful to use a self-signed certificate.  These are not in any way secure.  To generate a self-signed certificate, there is a utility in the proxy container `self-signed-certificate` that will generate one on demand after receiving key components of the CSR.

There is a self-signed certificate in the repo for testing generated with (on metal)

```
./bin/self-signed-certificate ssl GB London "Imperial College" reside web-dev.dide.ic.ac.uk
```

These can be used in the container by execing `self-signed-certificate /run/proxy` in the container while it polls for certificates.  Alternatively, to generate certificates with a custom CSR (which takes a couple of seconds) you can exec

```
self-signed-certificate GB London IC vimc montagu.vaccineimpact.org
```

### `dhparams` (Diffie-Hellman key exchange parameters)

We require a `dhparams.pem` file (see [here](https://security.stackexchange.com/questions/94390/whats-the-purpose-of-dh-parameters) for details.  To regenerate this file, run

```
./bin/dhparams ssl
```

from this directory, commit the result to git and rebuild the containers.  This takes quite a while to run (several minutes).  You can copy your own into the container at `/run/proxy/dhparams.pem` before getting the certificates in place.
