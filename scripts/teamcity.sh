#!/usr/bin/env bash
set -ex

# 8da5a52
docker pull vimc/orderly.server:master
docker pull vimc/orderly-web:master
docker pull vimc/orderlyweb-migrate:master

pip3 install --quiet -r requirements.txt
python3 setup.py test
