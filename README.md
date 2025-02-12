| Uses | ![alt text][Pi4B] | ![alt text][Pi3B] | ![alt text][IC-905] | ![alt text][Python] | ![alt text][POE++] | ![alt text][VLAN] | 
| --- | --- | --- | --- | --- | --- | --- |

[Pi4B]: https://img.shields.io/badge/-Pi%204B-green "Pi 4B"
[Pi3B]: https://img.shields.io/badge/-Pi%203B-orange "Pi 3B"
[IC-905]: https://img.shields.io/badge/-IC--905-cyan "IC-905"
[Python]: https://img.shields.io/badge/-Python%203.12-red "Python5"
[POE++]: https://img.shields.io/badge/-POE++-yellow "POE++"
[VLAN]: https://img.shields.io/badge/-VLAN-blue "VLAN"


This project is supporting efforts to understand and utilize the Icom IC-905 Controller to RF Unit ethernet messages to perform band decoder functions. The main goal is to extract PTT events and current RX/TX frequency from the ethernet cable physically close to the RF unit eliminating long control cable runs to tower mounted units to operate relays for antenna switching and amplifier control.  It also frees up the USB port for a local computer connection for logging and digital mode applications.

This is an undocumented protocol so Icom could change it in future firmware updates rendering these progams useless, be warned.

The normal supported RF Unit connection is a point to point ethernet cable using the RF Unit ethernet port.  There is another ethernet port for normal network control.

My test setup has 3 connections at minimum.  
1. Control head cable to a TP-Link TL-SG116E managed switch port 2.
2. Switch port 3 to a POE++ (LTPOE++ compatible in my case) 90W POE inserter.
3. POE inserter to the RF unit.  This must be on the RF Unit side of the switch closest to the RF Unit.
4. Port 16 is mirroring port 2.

Ports 2 and 3 are in a VLAN so the switch can handle other traffic and not interfere with the 905.

The long term setup for me will use 2 managed switches, my main shack 16-port TL-SG116E managed switch and a smaller 8-port TL-SG108E managed switch.  The 905 VLAN will use 802.1Q VLAN tagging and extend across the 2 switches.  Other devices will be in the shack and on the remote switch but their traffic will be logically isolated.

-----------------------------------------------

### Band Decoder programs

As of Feb 5, 2025 there are now 3 means to extract the PTT and frequency events.  

The first was a combination of a tcpdump utility command line script piped to a small Python program where additional filtering and information was printed out.  This was basically a prototype for a dedicated Python program.  Cpa905 output is piped to Proc905.py.  It is now in the Archive Folder

A standalone Python program TCP905.py was next.  It uses scapy module to prefilter data based on packet lengths of interest as before.  The TCP packet payload is extracted and parsed for PTT and frequency data.  It was run on Python 3.9.  It is now in the Archive folder.

The standalone Python TCP905v2.py program is the current version and uses message ID based processing instead of packet lengths and is easier to add and extend.  It requires Python 3.10 or higher.  I tested on v3.12.3 in Python's virtual dev environment on my PC and on Python 3.11 (not in a viirtual env) that came with the Pi OS Lite on a Pi3B.   

### TCP905v2.py Usage  (Current Dev)

I have created a Wiki page Building the Project for how to build and configure the program to run on a remote RPi board.
https://github.com/K7MDL2/IC905_Ethernet_Decoder/wiki/Building-the-Project

This uses a Pi 3B or Pi 4B to run our Band Decoder program and uses the GPIO pins to control relays and such.  The CPU must be connected so that it can monitor the TCP-IP traffic between the IC-905 control head and it's RF Unit.  I use a managed ethernet switch with VLAN and port mirrorng. The Pi plugs into the mirror port.

Here is how to set up a Pi 3B or Pi 4B to run the software 
https://github.com/K7MDL2/IC905_Ethernet_Decoder/wiki/Setup-on-a-Pi3B

This Wiki page (and others) https://github.com/K7MDL2/IC905_Ethernet_Decoder/wiki/Configuring-the-IO  shows how to configure the code and hardware for GPIO ouotput to control things like antenna switches and amplifier keying. 

We have to run the program as sudo or you get access denied from the the network layer I think.  Assuming you are in the folder where you installed the TP905v2.py program, in the Python virtual env the command line looks like this:
        
    sudo /home/pi/venv/bin/python ./TCP905v2.py

Without the venv, it is just:

    sudo python TCP905v2.py

The programs here are tested on a Windows PC and Pi 4B with Python 3.12.3 in the venv, and on a stripped down Pi 3B. It monitors the 905's RF Unit ethernet communication to operate as a band decoder located at or near the RF Unit, or a least close to it depending on where power for the POE inserter is located.  GPIO pins activate relays for antenna switching and perhaps amplifier selection and PTT.   GPIO pins will operate relays or other IO devices based on selected band and PTT state.   I have a relay Pi 'hat' with 3 relays on a Pi3B for example.  There is GPIO configuration information for direct, custom, and BCD output control patterns on this site's Wiki pages.  The BCD example will talk to my 905 Remote BCD Decoder board to provide 12 outputs, 6 PTT and 6 for Band.

![{EE40D230-11FF-4F5E-8067-A364F71EF05C}](https://github.com/user-attachments/assets/31102ccb-c4db-4b01-8da7-b14b4ef1c24f)


Details are provided here https://github.com/K7MDL2/IC905_Ethernet_Decoder/wiki/Configuring-the-IO about how to configure the GPIO output with examples for a PiHat Relay board and using a direct connection to my 905 USB Band decoder project Remote BCD decoder board which provides 6 buffered BAND outputs and 6 buffered PTT outputs for 6 bands.

This versoin program is the same as TCP905.py below except instead of filtering and processing packets based on packet lengths, I am using the 2nd and 3rd payload bytes as the message ID.  The 1st byte seems to always be 0x01.  2nd byte looks to be the message ID.  3rd byte is normally between 0 and 3 with a few exceptions.   

I have mapped out just about every required packet for reliable band decoding and PTT and weeded out the ones that are not useful.  In a few cases the same ID message presented totally different kinds of data.  I found a few more bytes to differentiate them and keep things clean.  Seem pretty robust now.  

Since we cannot query the radio, we can only glean what we see from the time we start our program.  The radio communication to the RF unit is primarily event driven and until an action at the controller happens, such as preamp, split, or VFO frequency, we do not know the current state.  Without a valid VFO frequency I cannot know what relays to operate so I block PTT until a good frequency is observed.  When you turn on the radio the 3rd message (a8 03) syncs up the radio and controller and the values we need are in there. 

There 2 solutions. 
1. Operate a radio screen or physical control.  Not every control will generate a (useful) message for us.  Changing a major setting like filter, mode, band, VFO, will and that will unblock PTT.
2. The best solution is to turn on our band decoder before the radio so we can see the initialization message.  Then we are ready to go.

Here is a shot of the heavily reformatted screen messages as of 11 Feb 2025.  I have aligned and colorized the various fields of most interest.

![image](https://github.com/user-attachments/assets/66a712eb-bb8d-444c-9264-af40477c0509)

You can see changes to some radio settings.  Many of these are not required for band decoder purposes but they are mostly always in the same message so why not.  It is helpful to me to spot any corruption of the messages I am relying on.  Frequency, thus our calculated band, PTT, and split are the absolute required items.  The rest are just FYI.  Since they are not important I have not bothered to translate the numeric values to Text labels.  The filter number I display is adjusted to match FIL1-FIL3 on the radio screen.  

You can see a few TX-RX events marked in RED and GREEN.  One has crossband split enabled so it invokes a band change along with a 0.3sec delay after changing the band output to the new VFO band furing TX and back tot ehg RX band after a short delay.  The key info is now colorized for easier visual tracking.

Having mapped out the messages and their lengths, The useful messages length are now known. The program starts by low leel filtering filtering allwoing p[acket length > 229 bytes.  66 bytes are TCP header stuff.  In my tables I have recorded the payload lengths and apply a max size filter early on.  There are a lot of large payloads containing spectrum related content and GPS data.  That leaves far fewer packets to process a we ony need a relative few. 

The message sequence for Tx/Rx transitions seem to vary by band and mode. I have tried many combinations and bekleive I have things covered.  There are several places in the code you can see what messages are passing by and optionally do a hexdump on them in a way that makes it easy to identify visually any changing bytes.

Here is one example of a PTT message sequence.   More info is in the Wiki pages along with a catalog of message IDs which can be updated as we learn more.  The ID_byte and the Attribute_Bytes are combined to create an ID value.

    SSB - No split - vfoB on same band also SSB
    
    e8 01 RX Idle
    e8 00 TX start when PTT pushed - like a trigger
    e8 01 get this after TX starts
    e8 00 TX End - trigger PTT change, now RX
    d8 01 frequency update
    50 03 NMEA data - this is not part of the regular sequence, just an example of a variety async packets mixed in.
    e8 01 RX idle

Below is a list of observed message IDs.  The code will always have the latest.

https://github.com/K7MDL2/IC905_Ethernet_Decoder/wiki/Message-ID-and-their-Functions

You can turn on print in the switch_case() method to see all IDs routed through to this list.
The function 'unhandled()' does nothing, it is used to squelch known messages so we can see unknown messages easier.  I only added message IDs that I have actually seen so we are not chasing ghosts.  Unknown messages, message IDs not in the list, end up in the default function where some info is printed out such as "Unknown Message, ID == 0xD301 Length = 306".

One pattern I might be seeing is some numeric groups of messages are assigned to certain modes.  Seems like being in DV, ATV, SSB, FM, CW, or RTTY causes a whole new group of spectrum-looking type messages.   You can tell if it is spectrum related by simply raising and lowering the reference level while watching the hexdumps.   When there is no visible spectrum on radio screen, most of the packets are filled then with 0s and/or they stop flowing until a signal or noise rises above the ref threshold.  Entering a menu usually stops spectrum data flowing.  You can see this behavior when running wfView, the spectrum drawing stops.

After looking at so many of these and how many have the same incomplete chunks of NMEA data in the messages, I am suspecting the 905 code is leaving old buffer data in the messages and not zeroing unused bytes out, or maybe these are uninitialized packet buffers.

It is a lot of typing and packet inspection but used this method to efficiently and accurately know what messages do what things an record that.  This approach is largely self-documenting.  It is easy to scan the list and expose message IDs of interest and also inpect the payloads while the rest of the program continues on.  The same information is often found in many different packets.  Contributors can update the list and add new functions for them easily.

PTT is now fairly robust and also accomodates split and duplex, swapping in the unselected VFO as active during transmit only.   Duplex and Split use the same byte, the only difference is that duplex sets VFOB to a programmed offset, I expect always in the same band.   The 905 will do cross band split so when duplex (and thus FM/DV type modes) is off, VFOB (aka unselected VFO) is returned to the prior non-duplex value.  This can be on any band.

Split is important to get right.  Lets say you have 1.2, 2.3 and 5.7GHz bands sharing a commmon wideband dish antenna.  You have each band connected to a SP3T coax switch and the switch common connected to the wideband antenna. Split is on, VFOB set to 5GHz band and RX is on 2.3GHz.  This means the antenna will be on the RF Unit's 2.3GHz RF jack in RX only.  5GHz will be disconnected.   When you TX it will output power on the 5GHz connector and TX into nothing unless we hold off PTT slightly to switch the 5G jack onto the dish antenna feed during TX.  Not only will no one hear you, it could be damaging for high power stuff downstream.  Thenon RX swith tthe 2.3G jack back onto the dish feedline.


### TCP905.py Usage  (Archived)

Prerequisites are scappy python module.  Can do a 'sudo pip install scappy' if you are missing it on your system.  You mnay also need other modules such as NumP.  Once you have the required modules, change permisison to make it executable in Linux (chmod 777 TCP905.py is one method).   Then just run the program, usually with ./TCP905.py.  Sometimes on Windows you may do better with Python3 ./TCP905.py.

This is what is shown on the screen today.   There are many debug lines available to see what lies under the hood but they are commented out to reduce the noise.

![{5CC56F77-3BA5-4E04-811F-E8A6A18BB169}](https://github.com/user-attachments/assets/3da194cd-1271-4369-9a4c-eb379c4d0303)


### Script Usage  (Archived)

Prerequisites are tcpdump utility.  Can do a 'sudo apt install tcpdump' if you are missing it on your system.
on the Pi command line

In the directory where your scripts are downloaded, run the following command

![{B754341F-3348-4FBB-B484-371D9CDB6658}](https://github.com/user-attachments/assets/89cba467-f293-41b3-bdd3-bd213ed8a367)

Hit Cntl+C to quit.

You can run the command in Cap905 on the command line by itself and alter the filter values to look at other things.

This is an example of the filterted and processed output as of 3 Feb 2025

![{00E975ED-C991-49BE-8E6F-841ED7ED576B}](https://github.com/user-attachments/assets/ec29406c-058c-40f6-b2e2-ede06eab98a7)


1. Visible info include the:

2. Band name

3. PTT state, RX or TX

4. Dial Frequency

5. Lower and Upper edges of the band search table

6. Offset used to convert the received VFO values to the actual dial frequency

7. Other hex data messages.  The indented ones are from raw packet capture utility filtered output.  I have not figured out how to shut those off yet.  They are not from the program itself but that is what is piped into the Python program.  Not every message appear to be proceeed when high message rates are shived int the Python program, likey due to buffering issues.   I will be looking to move the TCP sniffing function from the script into the Python program.
