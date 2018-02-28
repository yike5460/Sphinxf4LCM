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

# Prepare log file
sudo /bin/mkdir /var/log/vnflcv
sudo /usr/bin/touch /var/log/vnflcv/vnflcv-deployment.log
sudo chmod 646 /var/log/vnflcv/vnflcv-deployment.log

# Update the list of available packages and their versions
echo "================================================" >> /var/log/vnflcv/vnflcv-deployment.log
/bin/date >> /var/log/vnflcv/vnflcv-deployment.log
echo "1. Running apt-get update" >> /var/log/vnflcv/vnflcv-deployment.log
echo "================================================" >> /var/log/vnflcv/vnflcv-deployment.log
sudo /usr/bin/apt-get -y update >> /var/log/vnflcv/vnflcv-deployment.log

# Upgrade the packages to the latest versions
echo "================================================" >> /var/log/vnflcv/vnflcv-deployment.log
/bin/date >> /var/log/vnflcv/vnflcv-deployment.log
echo "2. Running apt-get upgrade" >> /var/log/vnflcv/vnflcv-deployment.log
echo "================================================" >> /var/log/vnflcv/vnflcv-deployment.log
sudo /usr/bin/apt-get -y upgrade &>> /var/log/vnflcv/vnflcv-deployment.log

sudo apt-get -y install zfsutils-linux &>> /var/log/vnflcv/vnflcv-deployment.log

# Remove the existing LXD packages
echo "================================================" >> /var/log/vnflcv/vnflcv-deployment.log
/bin/date >> /var/log/vnflcv/vnflcv-deployment.log
echo "3. Removing lxd and lxd-client" >> /var/log/vnflcv/vnflcv-deployment.log
echo "================================================" >> /var/log/vnflcv/vnflcv-deployment.log
sudo /usr/bin/apt-get -y remove --purge lxd lxd-client >> /var/log/vnflcv/vnflcv-deployment.log

# Install the snap version of LXD
echo "================================================" >> /var/log/vnflcv/vnflcv-deployment.log
/bin/date >> /var/log/vnflcv/vnflcv-deployment.log
echo "4. Installing lxd" >> /var/log/vnflcv/vnflcv-deployment.log
echo "================================================" >> /var/log/vnflcv/vnflcv-deployment.log
sudo /usr/bin/snap install lxd >> /var/log/vnflcv/vnflcv-deployment.log
/bin/sleep 20

# Initialize the LXD configuration
echo "================================================" >> /var/log/vnflcv/vnflcv-deployment.log
/bin/date >> /var/log/vnflcv/vnflcv-deployment.log
echo "5. Initializing lxd" >> /var/log/vnflcv/vnflcv-deployment.log
echo "================================================" >> /var/log/vnflcv/vnflcv-deployment.log
/snap/bin/lxd init --auto --storage-backend zfs >> /var/log/vnflcv/vnflcv-deployment.log
OIF=$(ip route get 8.8.8.8 | grep dev | cut -f 5 -d ' ')
OIF_MTU=$(cat /sys/class/net/${OIF}/mtu)
/snap/bin/lxc network create lxdbr0 bridge.mtu=${OIF_MTU} ipv4.address=auto ipv4.nat=true ipv6.address=none ipv6.nat=false >> /var/log/vnflcv/vnflcv-deployment.log

# Install conjure-up
echo "================================================" >> /var/log/vnflcv/vnflcv-deployment.log
/bin/date >> /var/log/vnflcv/vnflcv-deployment.log
echo "6. Installing conjure-up" >> /var/log/vnflcv/vnflcv-deployment.log
echo "================================================" >> /var/log/vnflcv/vnflcv-deployment.log
sudo /usr/bin/snap install conjure-up --classic >> /var/log/vnflcv/vnflcv-deployment.log

# Run conjure-up
echo "================================================" >> /var/log/vnflcv/vnflcv-deployment.log
/bin/date >> /var/log/vnflcv/vnflcv-deployment.log
echo "6. Running conjure-up" >> /var/log/vnflcv/vnflcv-deployment.log
echo "================================================" >> /var/log/vnflcv/vnflcv-deployment.log
if [ "$1" == "--headless" ]
then
    /snap/bin/conjure-up $(dirname $0) localhost
else
    /snap/bin/conjure-up $(dirname $0)
fi
