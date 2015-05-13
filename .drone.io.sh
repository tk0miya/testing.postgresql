#!/bin/sh
sudo apt-get update
sudo apt-get install python2.6 python2.6-dev python3.4 python3.4-dev

pip install --use-mirrors --upgrade wheel
pip install --use-mirrors --upgrade --use-wheel detox misspellings docutils "tox < 2.0"
pip install https://bitbucket.org/hpk42/detox/get/tip.zip
find src/ -name "*.py" | misspellings -f -
detox
