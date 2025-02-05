This project is supporting efforts to understand and utilize the Icom IC-905 Controller to RF Unit ethernet messages. The main goal is to extract PTT events and current RX/TX frequency from the ethernet cable physically close to the RF unit eliminating long control cable runs to tower mounted units to operate relays for antennas switching and amplifier control. 

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

The first was a combination of a tcpdump utility command line script piped to a small Python program where additional filtering and information was printed out.  This was basically a prototype for a dedicated Python program.  Cpa905 output is piped to Proc905.py.

A standalone Python program is now available called TCP905.py.  It uses scapy module to prefilter data based on packet lengths of interest as before.  The tcp packet payload is extracted and parsed for PTT and frequency data.  TCP905v2.py uses message ID based processing instead of packet lengths and is easier to add and extend.

The programs here are tested on a Pi4B and intended to learn (enough) about the 905 ethernet communication to operate a band decoder located at or near the RF Unit, or a least close to it depending on where power for the POE inserter is located.  Once the information needed is deemed reliable, I will extend the script to operate GPIO pins to activate relays for antenna switching and perhaps amplifier selection and PTT.   GPIO pins will operate relays or oter IO devices based on selected band and PTT state.   I have a relay Pi 'hat' with 3 relays on a Pi3B for example.  I will also set up BCD to talk to my 905 remote decoder board for 16 outputs (12 used - 6 PTT and 6 Band).

![{EE40D230-11FF-4F5E-8067-A364F71EF05C}](https://github.com/user-attachments/assets/31102ccb-c4db-4b01-8da7-b14b4ef1c24f)


### TCP905v2.py Usage  (Current Dev)

This is the same as TCP905.py below except instead of filtering and processing packets based on packet lengths, I am using the 2nd and sometimes the 3rd payload bytes as message IDs.  The 1st byte seems to always be 0x01.  2nd byte looks to be the message ID.  3rd byte is normally a 0x01 but occasionally is 0x02 or, as with the GPS data, 0x03.  

I mapped out the message IDs (for lengths >259 total packet size) for a series of activities and located bytes for split/duplex, preamp, atten, and sequencial order of IDs during PTT events. 

Here is one example of a PTT message sequence.  More will be on the Wiki pages along with a catalog of message IDs which can be updated as we learn more.  The 2nd and 3rd byte values are listed.  I actually only route on teh 2nd byte, the 3rd is optionally used in teh functions.  For example e8 00 is PTT change event.  e8 is normal state, both for TX and RX.

    SSB - No split - vfoB on same band also SSB
    
    e8 01 RX Idle
    e8 00 TX start when PTT pushed - like a trigger
    e8 01 get this after TX starts
    fc 00 ... heartbeat message likely every 1 second or so
    f8 00 maybe get this in middle one time
    fc 00 .... many until RX..    fc 00 streams with occasional f8 00 in middle
    e8 00 TX End - trigger PTT change, now RX
    d8 01 frequency update
    50 03 NMEA data - sometimes
    e8 01 RX idle

Below is a list of observed message IDs.  You can turn on print in the switch_case() method to see all IDs routed through to this list.
The function 'unhandled()' does nothing, it is used to squelch known messages so we can see unknown messages easier.  I only added message ID that I have actually seen so we are not chasing ghosts.  Unknown messages, message IDs not in the list, end up in the default function where some info is printed out such as "Unknown Message, ID == 0xD301 Length = 306".

Replace any of these with dump() to do a hexdump and help identify what it does.  See first line (commented out) as an example.
Lower the packet length filter size and you will see many more. Unclear if the smaller packets need to be looked at, seems like we have what we need.

    switch = {
    #0xYY: dump,  # example of a message routed to hex dump function for investigation
    0x10: unhandled,
    0x14: unhandled,
    0x18: case_x18,   # preamp and atten, likely more
    0x1c: unhandled,
    0x20: unhandled,
    0x24: unhandled,
    0x28: unhandled,
    0x2c: unhandled,
    0x30: unhandled, # 0x3003 is NMEA data
    0x34: unhandled,
    0x3c: unhandled,
    0x40: unhandled,
    0x48: unhandled,
    0x4c: unhandled,
    0x50: unhandled,
    0x54: unhandled,
    0x58: unhandled,
    0x5c: unhandled,
    0x60: unhandled,
    0x64: unhandled,
    0x68: unhandled,
    0x90: unhandled,
    0xb4: unhandled,
    0xb8: unhandled,
    0xbc: unhandled,
    0xc0: unhandled,
    0xc4: unhandled,
    0xc8: unhandled,
    0xcc: unhandled,
    0xd0: unhandled,
    0xd4: case_xD4,   # gerated for Split status change, likely more events.
    0xd8: frequency,  # D8 00 - comes in 2 lengths, one short and one with NMEA data added on.  Has split/duplex status in it
    0xdc: unhandled,
    0xe0: unhandled,
    0xe4: unhandled,
    0xe8: ptt,        # e8 00 tx/rx changover trigger, e801 normal RX or TX state.  PTT is last byte but may be in others also. Byte 0xef is PTT state
    0xf0: unhandled,  # fc 00 heartbeat message during TX
    0xf4: unhandled,
    0xf8: unhandled,  # f8 00 shows up periodically in middle of fc00 TX streams
    0xfc: TX_on,
    }

I converted to this method because I wanted to more efficiently and accurately know what messages do what things.  This approach is also somewhat self documenting as seen with the dump example it is easy to expose message IDs of interest while the rest of the program continues on.  The same information is often found in many different packets jsut waiting to be discovered.  Other contributors can update the list and add new functions for them easily.

PTT is fairly robust and also accomodates split and duplex, swapping in the unselected VFO as active during transmit only.   Duplex and Split use the same byte, the only difference is that duplex sets VFOB to a programmed offset, I expect always in the same band.   The 905 will do cross band split so when duplex (and thus FM type modes) is off, VFOB (aka unselected VFO) is returned to the prior non-duplex value.  This can be on any band.

I look in ID=0xd4 which is issued when split is enabled/disabled, and it can be found in the frequency update message ID=0xd8 at teh same byte location.  

Lets say you have 1.2, 2.3 and 5.7GHz bands sharing a commmon wideband dish antenna.  You have each band connected to a SP3T coax switch and the switch common connected to the wideband antenna. You have VFOB set to 5GHz band and are RX on 2.3GHz  This means the antenna will  be on the RF Unit 2.3GHz RF output.  5GHz will be disconnected.  Finally you have SPLIT turned ON.  Now when you TX it will outut power on the 5GHz connector and TX into nothing.  Not only will no one hear you, it could be damaging for high power stuff downstream.  


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
