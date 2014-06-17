#!/bin/sh
sudo apt-get update
sudo apt-get install python2.6 python2.6-dev python3.4 python3.4-dev

pip install --use-mirrors --upgrade detox misspellings docutils
find src/ -name "*.py" | misspellings -f -
detox
