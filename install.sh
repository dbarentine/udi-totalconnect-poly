#!/usr/bin/env bash

# If we are running on Polisy we need to pre-install the py37-zeep package. Otherwise pip will fail.
unameValue=$(uname -a)
if [[ $unameValue == *"polisy"* ]]; then
  echo "Installing py37-zeep"
  pkg update
  pkg install -y py37-zeep
fi;

pip3 install -r requirements.txt --user
