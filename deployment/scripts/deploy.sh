#!/bin/bash

# Adding hostname in /etc/hosts file
HOSTNAME=`cat /etc/hostname`
ETC_HOSTS=/etc/hosts
IP="127.0.1.1"
HOST_LINE="$IP\t$HOSTNAME"
if [ -n "$(grep $HOSTNAME $ETC_HOSTS)" ]
then
        echo "$HOSTNAME found in $ETC_HOSTS"
else
        echo "$HOSTNAME not found in $ETC_HOSTS. Adding now."
        sudo -- sh -c -e "echo '$HOST_LINE' >> /etc/hosts"
        if [ -n "$(grep $HOSTNAME $ETC_HOSTS)" ]
        then
                echo -e "$HOSTNAME was added succesfully in $ETC_HOSTS file \n $(grep $HOSTNAME $ETC_HOSTS)"
        else
                echo "Failed to add $HOSTNAME, Try again"
        fi
fi

# Update the list of available packages and their versions
echo "================================================"
/bin/date
echo "1. Running apt-get update"
echo "================================================"
sudo /usr/bin/apt-get -y update

# Upgrade the packages to the latest versions
echo "================================================"
/bin/date >> /var/log/vnflcv/vnflcv-deployment.log
echo "2. Running apt-get upgrade"
echo "================================================"
sudo /usr/bin/apt-get -y upgrade

sudo apt-get -y install zfsutils-linux

# Remove the existing LXD packages
echo "================================================"
/bin/date
echo "3. Removing lxd and lxd-client"
echo "================================================"
sudo /usr/bin/apt-get -y remove --purge lxd lxd-client

# Install the snap version of LXD
echo "================================================"
/bin/date
echo "4. Installing lxd"
echo "================================================"
sudo /usr/bin/snap install lxd
/bin/sleep 20

# Initialize the LXD configuration
echo "================================================"
/bin/date
echo "5. Initializing lxd" >> /var/log/vnflcv/vnflcv-deployment.log
echo "================================================"
/snap/bin/lxd init --auto --storage-backend zfs
OIF=$(ip route get 8.8.8.8 | grep dev | cut -f 5 -d ' ')
OIF_MTU=$(cat /sys/class/net/${OIF}/mtu)
/snap/bin/lxc network set lxdbr0 bridge.mtu ${OIF_MTU}
/snap/bin/lxc network set lxdbr0 ipv4.address auto
/snap/bin/lxc network set lxdbr0 ipv4.nat true
/snap/bin/lxc network set lxdbr0 ipv6.address none
/snap/bin/lxc network set lxdbr0 ipv6.nat false

# Install conjure-up
echo "================================================"
/bin/date
echo "6. Installing conjure-up"
echo "================================================"
sudo /usr/bin/snap install conjure-up --classic

# Run conjure-up
echo "================================================"
/bin/date
echo "6. Running conjure-up"
echo "================================================"
if [ "$1" == "--headless" ]
then
    /snap/bin/conjure-up $(dirname $0) localhost
else
    /snap/bin/conjure-up $(dirname $0)
fi
