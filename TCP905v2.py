#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  TCP905.py
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  
from scapy.all import *
import sys
import binascii
import numpy as np
#import codecs
from struct import *

  
#  These band edge values are based on the radio message VFO
#    values which have no offset applied
#  We use this value then once we know the band we can add the
#    fixed offset and then display the actual dial frequency

#  The 10G band values in this table are just dummy values until
#    the 10G transverter is hooked up to observe the actual values

Freq_table = { '2M': {
                    'lower_edge':144000000,
                    'upper_edge':148000000,
                        'offset':0
                },
                '70cm': {
                    'lower_edge':231000000,
                    'upper_edge':251000000,
                        'offset':199000000 
                },
                '23cm': {
                    'lower_edge':351000000,
                    'upper_edge':411000000,
                        'offset':889000000
                },
                '13cm': {
                    'lower_edge':562000000,
                    'upper_edge':712000000,
                        'offset':1738000000
                },
                '6cm': {
                    'lower_edge':963000000,
                    'upper_edge':1238000000,
                        'offset':4687000000
                },
                '3cm': {
                    'lower_edge':2231000000,
                    'upper_edge':2251000000,
                        'offset':99989000000
                }
            }
    
band_name = ""    
vfoa_band = ""
vfob_band = ""
selected_vfo = 0
unselected_vfo = 0
split_status = 0
preamp_status = 0
atten_status = 0
ptt_state = -1
payload_copy = ""
payload_copy = ""
payload_ID = 0
payload_byte2 = 0
offset = 0

#  __________________________________________________________________
#    
#  Main packet processing functions
#
#  __________________________________________________________________

def case_x18():  # process items in message id # 0x18
    global payload_copy
    global atten_status
    global preamp_status
    global payload_byte2
    
    #print("Preamp  len", len(payload_copy), "  extra byte", payload_byte2)
    #hexdump(payload_copy)
    if (payload_byte2 == 1):
        if (payload_copy[0x011d] == 1):
            atten_status = 1
        else:
            atten_status = 0

        if (payload_copy[0x011c] == 1):
            preamp_status = 1
        else: 
            preamp_status = 0

def case_xD4():    # process itgems in message #0xd4
    global payload_copy
    global split_status
    
    if (payload_copy[0x001b] == 1): # message #0xd4 @ 0x0001
        split_status = 1
    else:
        split_status = 0

def frequency():
    global payload_copy
    freq_last = 0
    global offset
    global band_name
    global selected_vfo
    global unselected_vfo
    global vfoa_band
    global vfob_band
    global split_status
    global ptt_state
    
    #hexdump(payload_copy)
    np.set_printoptions(formatter={'int':hex})
    #print(payload)
    
    # Duplex used split status byte for VFO swap, just has vfoB set different with offset
    # split is updated in message ID 0xD4.  here we can also pick it up and nto wait for 
    # someone to press the split button to generate the d4 event.
    split_status = payload_copy[0x001b]
    
    vfoa = get_freq(payload_copy, 0)
    #print("VFO A = ", vfoa)
    
    vfob = get_freq(payload_copy, 1)
    #print("VFO B = ", vfob)

    # Look for band changes
    if (vfoa != freq_last):
        # We changed frequencies - print it and do something with GPIO
        #print("\nReceived Uncorrected Frequency Value is ", freq)
        freq_last = vfoa
        
        # Search the Freq_table to see what band these values lie in
        for band_name in Freq_table:
            if (vfoa >= Freq_table[band_name]['lower_edge'] and
                vfoa <= Freq_table[band_name]['upper_edge'] ):
                # Found a band match, print out the goods
                offset = Freq_table[band_name]['offset'] 
                selected_vfo = vfoa + offset
                vfoa_band = band_name
                
            if (vfob >= Freq_table[band_name]['lower_edge'] and
                vfob <= Freq_table[band_name]['upper_edge'] ):
                # Found a band match, print out the goods
                offset = Freq_table[band_name]['offset'] 
                unselected_vfo = vfob + offset
                vfob_band = band_name
                
        print("VFO A Band = ", vfoa_band, "   Selected VFO = ", selected_vfo, "   unselected VFO = ", unselected_vfo)
        print("Split=",split_status, " Preamp=",preamp_status, " Atten=", atten_status)
        #print("  Lower edge = ", Freq_table[vfoa_band]['lower_edge'] + offset,
        #      "  Upper edge = ", Freq_table[vfoa_band]['upper_edge'] + offset,
        #      "  Offset = ", offset)
        # call GPIO here
    return vfoa_band

"""
PTT sequence 

SSB - No split - vfoB on same band also SSB
e8 01 RX
e8 00 TX start when Ptt pushed - like a trigger maybe
e8 01 get this after TX starts
fc 00 ...
f8 00 maybe get this in middle
fc 00 .... many until RX..    fc 00 streams with occasional f8 00 in middle
e8 00 TX End - trigger PTT change, now RX
d8 01 frequency update
50 03 NMEA data - sometimes
e8 01 RX idle

CW - No split
e8 01 RX
e8 00 TX start when Ptt pushed - like a trigger maybe
e8 01 get this after TX starts
...PTT down... ( no key applied)
e8 00 TX END, Now RX
d8 01 frequency info
50 03
e8 01 RX idle

SSB - Split On - vfoB on same band also SSB
e8 01 RX
e8 00 TX start when Ptt pushed - like a trigger maybe
e8 01 get this after TX starts
fc 00 ...
f8 00 maybe get this in middle
fc 00 .... many until RX..    fc 00 streams with occasional f8 00 in middle
e8 00 TX End - trigger PTT change, now RX
d8 01 frequency update
50 03 NMEA data 
e8 01 RX idle

SSB - Split ON, VFO b on different band, also SSB (may have been in CW on VFOB recheck)
e8 01 RX
e8 00 TX start when Ptt pushed - like a trigger maybe
e8 01 get this after TX starts
fc 00 ... many until RX..    fc 00 streams with occasional f8 00 in middle
e8 00 TX End Now in RX
d8 00 frequency update
50 ?? if split is on get this
e8 01 RX

FM - duplex 2M 
e8 01 RX
e8 00 TX start when Ptt pushed - like a trigger maybe
d0 00 TX start for some mix of conditions.  Not for split
e8 01 get this after TX starts
fc 00 ... 
f8 00  1x
fc 00 many until RX..    fc 00 streams with occasional f8 00 in middle
e8 00 TX End
d8 00 frequency update
30 03 NMEA string follows un-key likely for position and time update
e8 01 RX Idle

"""

def ptt():
    ptt_state_last = 255
    global ptt_state
    global vfoa_band
    global vfob_band
    global payload_copy
    global payload_ID
    global payload_byte2
    global split_status
    global selected_vfo
    global unselected_vfo
    selected_vfo_split_Tx = 0
    unselected_vfo_split_Tx = 0
    vfoa_band_split_Tx = 0
    
    # watch for PTT value changes
    if (vfoa_band != ""):   # block PTT until we know what band we are on
        if (not payload_byte2):
            ptt_state = payload_copy[0xef]
            #print("PTT state = ", ptt_state)
            if (ptt_state != ptt_state_last):
                if (ptt_state == 1):  # do not TX if the band is still unknown (such as at startup)
                    print("VFO A Band = ", vfoa_band, " ptt_state is TX ", ptt_state, " Msg ID ", hex(payload_copy[0x0001]))
                    # Call GPIO here
                    if (split_status == 1):
                        vfoa_band_split_Tx = vfoa_band  # back up the orignal VFOa band
                        selected_vfo_split_Tx = selected_vfo  # back up original VFOa
                        selected_vfo = unselected_vfo  # during TX assign b to a
                        vfoa_band = vfob_band

                if (ptt_state == 0):
                    print("VFO A Band = ", vfoa_band, " ptt_state is RX ", ptt_state, " Msg ID ", hex(payload_copy[0x0001]))
                    # Call GPIO here
                    if (split_status == 1):
                        vfoa_band = vfoa_band_split_Tx
                        selected_vfo = selected_vfo_split_Tx

                ptt_state_last = ptt_state
                
                # swap selected and unselected when split is on during TX
                print("VFO A Band = ", vfoa_band, "   Selected VFO = ", selected_vfo, "   unselected VFO = ", unselected_vfo)
                print("Split=",split_status, " Preamp=",preamp_status, " Atten=", atten_status)

def TX_on():
    print("Transmitting...")

def dump():
    global payload_copy
    hexdump(payload_copy)

def unhandled():
    return "unhandled message"

def case_default():
    global payload_copy
    global payload_ID
    global payload_byte2
    #ID = payload_copy[1:3].hex()
    #ID = payload_copy[1:3]
    #hexdump(payload_copy)
    payload_len = len(payload_copy)
    ID = unpack(">i",payload_copy[0:4])[0] ## convert bytes to unsigned int
    padding = 8
    ID = '0x'+hex(ID)[3:-1].zfill(4)
    print("Unknown message, ID = ", ID, "  Length = ", payload_len)
    return "no match found"

# These is a list of observed message IDs.  
# Turn on print in the switch_case() method to see all IDs routed through to this list
# unhandled does noting, squelches the known messages so we can see unknown messages easier
# Replace any of these with dump() to do a hexdump and help identify what it does.
# Lower the packet length fikter size and you will see many more. Unlcear if they need to be looked at.

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
    0xd4: case_xD4,   # Split
    0xd8: frequency,  # D8 00 - comes in 2 lengths, one short and one with NMEA data added on.
    0xdc: unhandled,
    0xe0: unhandled,
    0xe4: unhandled,
    0xe8: ptt,        # e8 00 tx/rx changover trigger, e801 normal RX or TX state.  PTT is last byte but may be in others also. Byte 0xef is PTT state
    0xf0: unhandled,  # fc 00 heartbeat message during TX
    0xf4: unhandled,
    0xf8: unhandled,  # f8 00 shows up periodically in middle of fc00 TX streams
    0xfc: TX_on,
}

# first byte of the payload always seems to be a 0x01.  Maybe it changes in sleep mode, TBD.
# The 2nd byte of the payload looks to be a message ID.
# The 3rd byte has values form 0 to 3 that I have observed so far.  Mostly 1 with 0 at times.
# This function is the message router.  
# Copies the payload into a global buffer in case it changes on us md way.
# Extracts the first 3 bytes into global vars
# then call the message function list indexed by message ID

def switch_case(payload):
    global payload_copy
    global payload_ID
    global payload_byte2
    
    payload_copy = payload
    payload_ID = payload[0x0001]
    payload_byte2 = payload[0x0002]
    #print("Switch on ",hex(payload_ID))
    return switch.get(payload_ID, case_default)()

    
# convert little endian bytes to int frequency 
def get_freq(payload, VFO):
    freq_hex_dec = np.array([0, 0, 0, 0],dtype=np.uint8)
    
    if VFO == 0:
        vfo = 0x00b8
    if VFO == 1:
        vfo = 0x00c4
        
    for i in range(0, 4, 1):
        freq_hex_dec[i] = (payload[vfo+i])
    #print(freq_hex_dec)

    # Convert from ascii array to binary hex byte string
    freq_hex_str = freq_hex_dec.tobytes()
    #print(freq_hex_str)
    
    # Flip from little to big endian
    byte_data = bytes(freq_hex_str)
    little_endian_bytes = byte_data[::-1]
    little_endian_hex_str = little_endian_bytes.hex()
    freq = int(little_endian_hex_str, base=16)
    #print(freq)
    # Now we have a decimal frequency
    return freq
#
#  __________________________________________________________________
#    
#  Main packet processing function
#
def parse_packet(packet):
    conf.verb = 0
    global band_name
    global vfoa_band
    global vfob_band
    global atten_status
    global preamp_status
    global split_status
    
    """sniff callback function.
    """
    if packet and packet.haslayer('TCP'):
        tcp = packet.getlayer('TCP')
        #tcp.show()
        payload = bytes(tcp.payload)
        #print(payload)
        #hexdump(payload)
        payload_len = len(payload)
        #print("Payload Length = ", payload_len)
        if (payload_len > 16):
            switch_case(payload)
        
        #print("Split:", split_status, " Preamp:", preamp_status, " Atten", atten_status)
        
  
  
def tcp_sniffer(args):     
    try:
        # can read from piped data input
        #payload = sys.stdin.readline()
        #print(payload)
        
        # filter and capture packets of interest using scapy functions
        a = sniff(
            #filter="tcp and port 50004 and (length == 290 or length == 304 or length == 306 or length == 308)",
            #filter="tcp and port 50004 and (greater 279 and less 310)",
            filter="tcp and port 50004 and greater 229",
            #filter="tcp and port 50004 and greater 70",
            iface=r'eth0',
            prn=parse_packet
            )
                
    except KeyboardInterrupt:
        print('Done', i)


if __name__ == '__main__':
    import sys
    sys.exit(tcp_sniffer(sys.argv))
