This project is supporting efforts to understand and utilize the Icom IC-905 Controller to RF Unit ethernet messages. The main goal is to extract PTT events and current RX/TX frequency from the ethernet cable physically close to the RF unit eliminating long control cable runs to tower mounted units to operate relays for antennas switching and amplifier control. 

This is an undocumented protocol so Icom could change it in future firmware updates rendering these progams useless, be warned.

The normal supported RF Unit connection is a point to point ethernet cable using the RF Unit ethernet port.  There is another ethernet port for normal network control.

My test setup has 3 connection at minimum.  
1. Control head cable to a TP-Link TL-SG116E managed switch port 2.
2. Switch port 3 to a POE++ (LTPOE++ compatible in my case) 90W POE inserter.
3. POE inserter to the RF unit.  This must be on the RF Unit side of the switch closest to the RF Unit.
4. Port 16 is mirroring port 2.

Ports 2 and 3 are in a VLAN so the switch can handle other traffic and not interfere with the 905.

The long term setup for me will use 2 managed switches, my main shack 16-port TL-SG116E managed switch and a smaller 8-port TL-SG108E managed switch.  The 905 VLAN will use 802.1Q VLAN tagging and extend across the 2 switches.  Other devices will be in the shack and on the remote switch but their traffic will be logically isolated.


As of Feb 4, 2025 there are now 2 means to extract the PTT and frequency events.  

The first was a combination of a tcpdump utility command line script piped to a small Python program where additional filtering and information was printed out.  This was basically a prototype for a dedicated Python program.  Cpa905 output is piped to Proc905.py.

A standalone Python program is now avaiable called TCP905.py.  It uses scapy module to prefilter data bansed n packet lengths of interest as before.  The tcp packet payload is extracted and parsed for PTT and frequency data.

The programs here are tested on a Pi4B and intended to learn (enough) about the 905 ethernet communication to operate a band decoder located at or near the RF Unit, or a least close to it depending on where power for the POE inserter is located.  Once the information needed is deemed reliable, I will extend the script to operate GPIO pins to activate relays for antenna switching and perhaps amplifier selection and PTT.

### TCP905.py Usage

Prerequisites are scappy python module.  Can do a 'sudo pip install scappy' if you are missing it on your system.  You mnay also need other modules such as NumP.  Once you have the required modules, change permisison to make it executable in Linux (chmod 777 TCP905.py is one method).   Then just run the program, usually with ./TCP905.py.  Sometimes on Windows you may do better with Python3 ./TCP905.py.

This is what is shown on the screen today.   There are many debug lines available to see what lies under the hood but they are commented out to reduce the noise.



### Script Usage

Prerequisites are tcpdump utility.  Can do a 'sudo apt install tcpdump' if you are missing it on your system.
on the Pi command line

In the directory where your scripts are downloaded run the following command

![{B754341F-3348-4FBB-B484-371D9CDB6658}](https://github.com/user-attachments/assets/89cba467-f293-41b3-bdd3-bd213ed8a367)

Hit Cntl+C to quit.

You can run the command in Cap905 on the command line by itself and alter the filter values to look at other things.

This is an example of the output as of 3 Feb 2025

![{00E975ED-C991-49BE-8E6F-841ED7ED576B}](https://github.com/user-attachments/assets/ec29406c-058c-40f6-b2e2-ede06eab98a7)


Visible info include the 
Band name
PTT state, RX or TX
Dial Frequency
Lower and Upper edges of the band search table
Offset used to convert the received VFO values to the actual dial frequency

The other hex data messages (indented ones) are from raw packet capture utitily filterted output.  I have not figured out how to shut those off yet.  They are not from the program itself.
