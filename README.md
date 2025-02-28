| Uses | ![alt text][Pi5B] | ![alt text][Pi4B] | ![alt text][Pi3B] | ![alt text][IC-905] | ![alt text][Python311] | ![alt text][Python312] | ![alt text][POE++] | ![alt text][VLAN] | 
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

[Pi5B]: https://img.shields.io/badge/-Pi%205B-purple "Pi 5B"
[Pi4B]: https://img.shields.io/badge/-Pi%204B-green "Pi 4B"
[Pi3B]: https://img.shields.io/badge/-Pi%203B-orange "Pi 3B"
[IC-905]: https://img.shields.io/badge/-IC--905-cyan "IC-905"
[Python311]: https://img.shields.io/badge/-Python%203.11-red "Python311"
[Python312]: https://img.shields.io/badge/-Python%203.12-red "Python312"
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

My long term setup, now installed, uses 2 managed switches. A 16-port TL-SG116E in the shack and a smaller 5-port TL-SG105E out in the remote outdoor box where my transverters, amps, and 12/28V power is located.  The 905 VLAN will use 802.1Q VLAN tagging and extends across the 2 switches creating a pipeline through the switches connecting the controller to the POE++ Inserter and RF Unit.  Other devices will be in the shack and on the remote switch but their traffic will be logically isolated.   I will have more on the actual VLAN set in the Wiki pages. I noted several times at power up the RF Unit speed was 100 instead of 1000 as normal.  ATV now works without crashing the radio connection.   Maybe coincidence.  Time will tell.   Separate issue, a Pi 3B cannot handle the ATV data rate.  The Pi 5 does fine, likely a Pi4B will be OK.     

Here is the setup in my outdoor cabinet about 100 cable feet away.   The RF Unit is 50 feet away from the cabinet on a rotating mast with a 600-6000MHz dish.  All 3 RF Unit connectors feed into a coax switch then to the dish.  I am only RX on 144 and 432.  Have other radios with power covering those bands, as I do 1296 but none of them rotate due to HOA restrictions and trees.

![20250227_155205](https://github.com/user-attachments/assets/dd922517-a93b-45ec-8764-4ff197c8f9e4)

![20250227_155225](https://github.com/user-attachments/assets/685b5214-8131-4bd3-a8c8-87b5586433f2)

I only need to switch 1 antenna among the 3 RF outputs so I am using a 28V SP6T coax switch with a relay 'HAT" on the Pi which is located in the remote cabinet on the ground.  50ft of rotator cable will run to the coax switch mounted next to the RF Unit to keep the coax jumpers short.

I used a Pi3B for most of my development. It works for everything except ATV mode where the data rate overwhelms the Pi 3B CPU.  The Pi4B might work but I do not have a free one handy to test with.  The Pi 5B works fine in ATV mode and the install script works on all 3 models.  Since I am not using ATV for now I have hte Pi 3B installed outside.  I am testing the Pi 5 on the bench mirrored to radio VLAN on the house side switch.

Here is my Pi 5B in an aluminum case with the top removed and a 4-relay Pi HAT board installed with the DHT11 temp sensor.  Below the relays are an NVMe SSD board and a Pi 5 fan cooler.   It will replace the Pi3B.

![20250226_185834](https://github.com/user-attachments/assets/b232bc76-10e3-4e41-b0e6-47207f4a69cc)

![20250226_190148](https://github.com/user-attachments/assets/af34a859-4d7f-4593-9f1b-9aae571491c5)

Here is a Pi 3B with a BEVRLink 4-channel Relay HAT board that will operate a up to 4 ports on the SP6T coax switch out at the RF unit.  I picked 4 relays so I have the option of using it as a 3-wire BCD + PTT to my Remote BCD Decoder board.  The Pi will be 100ft for the house and there is 50ft more to the RF Unit.  The blue device is a DHT11 temp and humidity sensor, more on that below.

![20250217_210707](https://github.com/user-attachments/assets/e6b00f2f-1630-45c5-92c6-0372456de6d6)

Here is a view between the relay and CPU board with a fan-cooled heat sink now mounted.  Despite the relay HAT having an already tall header, it was not enough to clear the heat sink.  I used a 2x20 row extender and some 2.5mm hex standoffs to raise the board and the fan cooler now has lot so airflow room.  The CPU is sitting on the bottom half of a 3D printed enclosure.  

![20250217_211132](https://github.com/user-attachments/assets/fecfcc09-ab11-4572-8b31-a3a69cc97189)

The aluminum plate under the CPU a Budd die cast box.  I am thinking of mounting the CPU to the plate along with a bulkhead ethernet jack and cable connector of some type TBD for the external relays it will control.  With the plate on the bottom the box becomes a weatherproof cover and can transfer internal heat to the outside (and the other way around).  It may need vent holes with a insect filter added in the plate under the CPU, TBD.  I could also put a small 12 or 28V to 5V 3A DC-DC converter inside if it was to be remote mounted someday.  In my first usage it will get 5V externally since I also need 5V@A for the TL-SG105E managed switch that will be near it and the POE injector in my outside cabinet.  28V need to get the relays for the coax switch control on 3 of the relays. 

The DHT11 and fan wire connections were not very secure and I wanted to fan to switch on and off according to temperature.  I assembled a small perfboard with JST connectors and a PN2222A transistor to switch the fan.  I soldered the JST plug side pins directly on to the DHT11 pins so it just plugs into the board and I do not need to mount it separately.  I can unplug it and build an extension cable if I find the sensor is too close to the CPU.

![20250220_101713](https://github.com/user-attachments/assets/11fea046-59ec-4f0a-8697-f2f1d9b8a58c)

The 4th relay supplies 28V to the POE injector so I can remotely toggle the power if needed.  I have had a number of random connection losses and I have some shaky evidence that when the RF Unit and Controller lose connection, the recovery is difficult without power cycling as the radio would normally do directly connected.   Power cycling the POE injector seems to help recover the connection (based on limited testing).  Automating the power relay automation will be difficult.  The delay for the POE inserter to fully power on is longer than the last ARP message which is when the controller gives up.  Upon loss the RF Unit will issue ARP 5 times but if the controller has already given up it will not connect.  I have seen one time where the controller continued to VFO changes but not received anything on the spectrum or audio.

-----------------------------------------------

### Band Decoder programs

As of Feb 5, 2025 there are now several program methods to extract the PTT and frequency events.  

The first was a combination of a tcpdump utility command line script piped to a small Python program where additional filtering and information was printed out.  This was basically a prototype for a dedicated Python program.  Cap905 output is piped to Proc905.py.  It is now in the Archive Folder

A standalone Python program TCP905.py was next.  It uses scapy module to prefilter data based on packet lengths of interest as before.  The TCP packet payload is extracted and parsed for PTT and frequency data.  It was run on Python 3.9.  It is now in the Archive folder.

The standalone Python TCP905v2.py program uses message ID based processing instead of packet lengths and is easier to add and extend.  It requires Python 3.10 or higher.  I tested on v3.12.3 in Python's virtual dev environment on my PC and on Python 3.11 (not in a virtual env) that came with the Pi OS Lite on a Pi3B.   

### TCP905.py Usage  (Current Dev)

TCP905v2.py has been replaced with v3 and moved to the Archive folder.  v2 used scapy.py module but scapy has a memory leak I was not able to work around.  Nearly every message received ticked up memory usage until after 4-6 hours the CPU memory was at 100% causing the OS to bog down, remote access to fail, and eventually the program crashes to be restarted (as desired).  It started up with 10% CPU and 9% memory.

In v3 I run tcpdump as a Python subprocess, piping it's unbuffered output into the program where I then parse out the packet and payload lengths and the payload data.  It uses about 3.7% memory and CPU varies from near 0% up to 100% instantaneously when processing a very high rate of events such as rapidly spinning the VFO for a long duration.  Since tcpdump is configured to only pass along packets > 229 bytes, and the program tosses packets > 360 bytes, between messages the program sits nearly idle and consuming almost no CPU and memory stays constant.

A feature just added is CPU and external temperature and humidity from a DHT11 sensor.  The main reason to develop this ethernet version of band decoder is to leverage the radio's ethernet and break out decoding info near the RF unit which is likely mounted on a mast or tower.  It will be at times in extreme temps so it would be good to record those temps.  I added code for a DHT11 one-wire sensor which is very common and inexpensive.  The data is logged periodically (120 seconds by default), printed at the end of the event line which is stored in the log file in /tmp/Decoder905.log.  Evenually this data will be stored in its own history file.   The install script sets up the GPIO pin and dtoverlay= line in /boot/firmware/config.txt so the OS can read the device.  No 3rd party modules are required with the latest OS version (bookworm).  A one line script 'chk_dht11' will check the OS is reading the device properly.  The device specs say the DHT11 only reads down to 32F (0C) so a better sensor may be in the future.  It was what I had here.  There is a variable at the top of the TCP905.py file to turn it in or off.  It is on by default.  The temp read function runs in a separate thread if there is a problem reading it, and a bus timout occurs (1sec each read attempt), it keep trying and no impact is made to the main radio message processing portion of the program.

Here is the latest screen shots with the version startup banner and you can see the GPIO pin assignments and patterns.  

![{0EA4CB3E-4119-487A-A2E6-752973DDE5BD}](https://github.com/user-attachments/assets/59f244a6-546c-4cc3-a7ae-628b58333e4a)

I have since added time-stamped temperature/humidity data message with it's own message label (TEMP ).  That data is also output to a separate log file /tmp/Temperatures.log.  That may be relocated in the near future to somewhere like /.

![{BE7193F2-4792-4459-96F0-9521A76AFB52}](https://github.com/user-attachments/assets/390eda56-f7fc-4145-8ad4-d4697868b416)

Install scripts are updated and I am using the generic progam name TCP905.py. I have started to change doc references to leave out the version part of the name.

I have created a Wiki page Building the Project for how to build and configure the program to run on a remote RPi board.
https://github.com/K7MDL2/IC905_Ethernet_Decoder/wiki/Building-the-Project

This uses a Pi 3B or Pi 4B.  I have a Pi 5 coming soon, requires different GPIO library.  This program uses GPIO pins to control relays and such.  The CPU board wired LAN port must be connected so that it can monitor the TCP-IP traffic between the IC-905 control head and it's RF Unit.  I use a managed ethernet switch(es) with 802.1Q VLAN tagging and port mirroring. The Pi plugs into the mirror port.

Use the link below to set up a Pi 3B or Pi 4B OS image to run the software.  Once you have a remote connection and copy down the repository, you can run an install script.  It will update the OS, install the dependent Python modules, then installs the program files as a systemd service.  Systemd will restart the program if it fails within 2 seconds.  The screen output is redirected to a log file.  The script view_log will tail the log file displaying any new events real-time with all it's color glory.  You can look in /tmp/Decoder905.log for past events.  This permits easy remote monitoring over an SSH connection.   https://github.com/K7MDL2/IC905_Ethernet_Decoder/wiki/Setup-on-a-Pi3B

This Wiki page (and others) https://github.com/K7MDL2/IC905_Ethernet_Decoder/wiki/Configuring-the-IO  shows how to configure the code and hardware for GPIO output to control things like antenna switches and amplifier keying.   This includes a BCD output config example.

The programs here are tested on a Windows PC (no GPIO) and Pi 4B with Python 3.12.3 in the venv, and on a Pi 3B under Python 3.11.2.  It monitors the 905's RF Unit ethernet communication to operate as a band decoder located at or near the RF Unit, or a least close to it depending on where power for the POE inserter is located.  GPIO pins activate relays for antenna switching and perhaps amplifier selection and PTT for each band.   I have a Pi 'hat' with 4 relays on a Pi3B for example.  There is GPIO configuration information for direct, custom, and BCD output control patterns on this site's Wiki pages.  The BCD example will talk to my 905 Remote BCD Decoder board to provide 12 outputs, 6 PTT and 6 for Band.  I access the Pi 3B via the Wifi inteface usually with SSH but with the right VLAN config you can also use the wired port.

![{EE40D230-11FF-4F5E-8067-A364F71EF05C}](https://github.com/user-attachments/assets/31102ccb-c4db-4b01-8da7-b14b4ef1c24f)

Inteh current v3 and later versions you can run TCP905.py withot sudo.   For the older versions run the program as sudo or you get access denied from the the network layer I think.  Assuming you are in the folder where you copied the TP905 program, in the Python virtual env the command line looks like this:
        
    sudo /home/pi/venv/bin/python ./TCP905.py

Without the venv as on the Pi 3B instructions, it is just:

    sudo python TCP905.py

As of 13 Feb 2025 there is an install script which sets up the program as a background service and you view the log file to see the screen output with 'tail-f /tmp/Decoder905.log', or use the view_log script to do the same thing.

Details are provided here https://github.com/K7MDL2/IC905_Ethernet_Decoder/wiki/Configuring-the-IO about how to configure the GPIO output with examples for a PiHat Relay board and using a direct connection to my 905 USB Band decoder project Remote BCD decoder board which provides 6 buffered BAND outputs and 6 buffered PTT outputs for 6 bands.

This version program is similar to the earlier TCP905.py below except instead of filtering and processing packets based on packet lengths, I am using the 2nd and 3rd payload bytes as the message ID.  The 1st byte seems to always be 0x01.  2nd byte looks to be the message ID.  3rd byte is normally between 0 and 3 with a few exceptions.   

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
