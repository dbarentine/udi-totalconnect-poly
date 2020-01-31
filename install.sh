#!/usr/bin/env bash

{
    # If we are running on Polisy we need to pre-install the py37-zeep package. Otherwise pip will fail.
    unameValue=$(uname -a)
    echo "uname = $unameValue"

    if echo "$unameValue" | grep -q "polisy"; then
      echo "Installing py37-zeep"
      pkg update
      pkg install -y py37-zeep
    else
      echo "Skipping py37-zeep install"
    fi;

    pip3 install -r requirements.txt --user
} > totalconnect-install.log