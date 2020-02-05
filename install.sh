#!/usr/bin/env bash

{
    # If we are running on Polisy we need to pre-install the py37-zeep package. Otherwise pip will fail.
    platform="$(uname -i)"
    polisyPlatform="POLISY"

    echo "Current Shell: $SHELL"
    echo "Platform: $platform"

    if [ "$platform" = "$polisyPlatform" ]; then
      echo "Installing py37-zeep"
      sudo -u polyglot /usr/sbin/pkg update
      sudo -u polyglot /usr/sbin/pkg install -y py37-zeep
    else
      echo "Skipping py37-zeep install"
    fi;

    pip3 install -r requirements.txt --user
} > totalconnect-install.log 2>&1