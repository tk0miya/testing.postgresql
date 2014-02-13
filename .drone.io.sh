#!/bin/sh
sudo apt-get update
sudo apt-get install python2.6 python2.6-dev

pip install --use-mirrors --upgrade detox misspellings
find src/ -name "*.py" | misspellings -f -
detox
