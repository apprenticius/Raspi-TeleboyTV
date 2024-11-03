# Raspi-TeleboyTV
TeleboyTV with Raspberry Pi 4B

It simulates a web browser on one side and a TV recorder on the other side.

Using HDMI-CEC it is possible to change channels with remote control of your TV. Furthermore for the power consumption the Raspberry Pi uses the USB connection from the television.

Prerequisites
  - Raspberry Pi 4B with Raspbian OS
  - MPV player installed on Raspberry Pi
  - User Account with Teleboy TV
  - Edit your channel list under https://www.teleboy.ch/sender

The channel list is used as the list of channels in the virtual vcr.

Finnally one have to enable auto start of the script virtual_vcr.py. Therefore one copies the file virtual_vcr.desktop to the folder /etc/xdg/autostart.

Don't forget to edit user and password in virtual_vcr.py!
