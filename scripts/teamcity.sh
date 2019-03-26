#!/usr/bin/env bash
set -ex
docker pull vimc/orderly.server:master
docker pull docker.montagu.dide.ic.ac.uk:5000/orderly-web:master
docker pull docker.montagu.dide.ic.ac.uk:5000/orderlyweb-migrate:master

pip3 install --quiet -r requirements.txt
python3 setup.py test
