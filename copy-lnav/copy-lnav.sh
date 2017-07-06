#!/bin/bash

if [ "$#" -ne 1 ]; then
   echo "usage: $0 <machine>"
   exit 1
fi

if [ ! -f /usr/local/bin/lnav ]; then
    pushd /tmp
    wget https://github.com/tstack/lnav/releases/download/v0.8.2/lnav-0.8.2-linux-64bit.zip -O /tmp/lnav-0.8.2-linux-64bit.zip
    unzip lnav-0.8.2-linux-64bit.zip
    sudo cp /tmp/lnav-0.8.2/lnav /usr/local/bin/
    popd
else
    echo "lnav found in this system"
fi

ssh-copy-id root@$1
scp /usr/local/bin/lnav root@$1:/usr/local/bin
#ssh $1 "for node in \`grep HostName /root/.ssh/config | awk '{ print $2 }'\`; do scp /usr/local/bin/lnav \$node:/usr/local/bin/lnav; done"
ssh root@$1 'for node in `grep HostName /root/.ssh/config | cut -d " " -f 6`; do scp /usr/local/bin/lnav $node:/usr/local/bin/lnav; done'
