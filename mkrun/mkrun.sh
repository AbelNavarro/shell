#!/bin/bash -x

if ((EUID)); then
  echo "You must be root."
  exit 1
fi

if [[ $# -lt 3 ]]; then
  echo "Illegal number of parameters."
  echo "Usage: $0 cloud_slot params_file mkcloud_target"
  echo "i.e. $0 1 params-c8-gate-ha plain"
  exit 1
fi

# Cloud slot
slot=$1
shift

# Params file
source $1
shift

# setup/create lvm disk
mkcloud_disk=/root/mkcloud.disk
if ! [ -f $mkcloud_disk ] ; then
  fallocate -l 200G $cloud_disk
fi

lolo=$(losetup | grep loop | awk '{ print $1 }')
if [[ ! $lolo ]]; then
  losetup -f $mkcloud_disk
  lolo=$(losetup | grep loop | awk '{ print $1 }')
fi

if [[ $(vgdisplay) ]]; then
  echo "Volumes already setup."
else
  echo "No volumes setup. Please run with 'setuphost' target first"
  exit 1
fi

export cache_clouddata=1
#export http_proxy=localhost:3128

export cloudpv=${lolo}
#export cloud=cloud
#export net_fixed=192.168.150
#export net_public=192.168.151
#export net_admin=192.168.152
#export vcpus=2

n=$slot
source /home/abel/work/automation/scripts/mkcloudhost/cloudfunc

export net_admin=$(cloudadminnet $n)
export net_ironic=$(cloudironicnet $n)
export net_public=$(cloudpublicnet $n)
export adminnetmask=255.255.254.0
export virtualcloud=$vcloudname$n
export cloud=$virtualcloud
export NOSETUPPORTFORWARDING=1

exec /home/abel/work/automation/scripts/mkcloud "$@"
