#!/bin/bash

# This sets the pin for a DHT11 temp humidity sensor
# This script updates /boot/firmware/config/txt to let the OS talk to the sensor
# after reboot you can use this command to see if the device is connected and working OK.
#   cat /sys/bus/iio/devices/iio:device0/in_temp_input 
#  
DT11_PIN="15"

echo "Do not run this script as sudo!"
cd /home/$USER

ifconfig > if_dump
sudo apt update
sudo apt upgrade
python --version
sudo apt install tcpdump
sudo apt install python3-numpy
sudo apt install python3-RPi.GPIO

echo "Updating /boot/firmware/config.txt for DHT11 temp sensor GPIO pin"
CONFIG="/boot/firmware/config.txt"
sudo sed -i "/dtoverlay=dht/d" $CONFIG
echo "dtoverlay=dht11,gpiopin=$DT11_PIN" | sudo tee --append $CONFIG

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

