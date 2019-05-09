#!/bin/bash

if [ "$#" -ne 1 ]; then
   echo "usage: $0 <machine>"
   exit 1
fi

if [ ! -f /usr/local/bin/lnav ]; then
    pushd /tmp
    wget https://github.com/tstack/lnav/releases/download/v0.8.5/lnav-0.8.5-linux-64bit.zip -O /tmp/lnav-0.8.5-linux-64bit.zip
    unzip lnav-0.8.5-linux-64bit.zip
    sudo cp /tmp/lnav-0.8.5/lnav /usr/local/bin/
    popd
else
    echo "lnav found in this system"
fi

if [ ! -f pass.txt ]; then
    uname -a | cut -d ' ' -f1 | tr '[:upper:]' '[:lower:]' > pass.txt
fi

sshpass -f pass.txt ssh-copy-id root@$1

ssh -q root@$1 [[ -f /usr/local/bin/lnav ]] || scp /usr/local/bin/lnav root@$1:/usr/local/bin
ssh root@$1 'for node in `grep HostName /root/.ssh/config | cut -d " " -f 6`; do scp /usr/local/bin/lnav $node:/usr/local/bin/lnav; done'
