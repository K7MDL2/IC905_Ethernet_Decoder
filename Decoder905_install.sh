#!/bin/bash

echo "Do not run this script as sudo!"
cd /home/$USER

ifconfig > if_dump
sudo apt update
sudo apt upgrade
python --version
sudo apt install pip
#sudo apt install python3-scapy
sudo apt install tcpdump
sudo apt install python3-numpy
sudo apt install python3-RPi.GPIO

DIR="/home/$USER/IC905_Ethernet_Decoder"

echo "Stopping Decoder905 service if already installed"
sudo systemctl stop Decoder905.service
sudo systemctl disable Decoder905.service

echo "Removing old files"
sudo rm /etc/systemd/system/Decoder905.service
sudo rm /usr/lib/systemd/system/Decoder905.service
sudo rm /tmp/Decoder905.log
rm ifconfig
rm view_log

echo "Resetting systemd"
sudo systemctl daemon-reload
sudo systemctl reset-failed

echo "Copying files and configuring the new systemd service ..."
sudo cp $DIR/TCP905.py /usr/local/bin
sudo chmod 744 /usr/local/bin/TCP905.py
cp $DIR/view_log /home/$USER
chmod +x /home/$USER/view_log

echo "Installing new Decoder905 service"
sudo cp $DIR/Decoder905.service  /etc/systemd/system/Decoder905.service
sudo chmod 664 /etc/systemd/system/Decoder905.service

echo "Restarting systemctl daemon ..."
sudo systemctl daemon-reload
sudo systemctl enable Decoder905.service
sudo systemctl reset-failed

# pause here and ask for reboot
while true; do
read -p "Reboot to finish.  Do you want to proceed? y/n " yn
case $yn in
	[yY] ) echo ok, we will proceed;
		break;;
	[nN] ) echo exiting...;
		exit;;
	* ) echo invalid response;;
esac
done

sudo reboot

