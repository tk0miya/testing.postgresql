#!/bin/sh
sudo apt-get update
sudo apt-get install python2.6 python2.6-dev python3.4 python3.4-dev

pip install --use-mirrors --upgrade wheel
pip install --use-mirrors --upgrade --use-wheel detox misspellings docutils "eventlet<0.16"
find src/ -name "*.py" | misspellings -f -
detox
