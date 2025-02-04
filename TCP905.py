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
    
    
#  Main packet processing function
def parse_packet(packet):
    TX = "\x01"
    RX = "\x00" 
    freq_last = 0
    dial_freq = 0
    offset = 0
    conf.verb = 0
    global band_name
    unselected_vfo = 0

    """sniff callback function.
    """
    if packet and packet.haslayer('TCP'):
        tcp = packet.getlayer('TCP')
        #tcp.show()
        payload = bytes(tcp.payload)
        #print(payload)
        #hexdump(payload)
        payload_len = len(payload)
        print("Payload Length = ", payload_len)
        
    # watch for PTT value changes
    ptt_state = -1
    ptt_len = 240    # PTT info
    if (payload_len == ptt_len):
        ptt_state = 0x01 & payload[ptt_len-1]
        #print(ptt_state)
        if (ptt_state == 1):
            print("Band = ", band_name, " ptt_state is TX ", ptt_state)
            # Call GPIO here
        #ptt_state = payload.find(RX, 17, 19)
        if (ptt_state == 0):
            print("Band = ", band_name, " ptt_state is RX ", ptt_state)
            # Call GPIO here
    
    # Compute what Band we are
    #else:   
    #Extract the 4 byte frequency value
    freq_len1 = 220   # frequency info
    freq_len2 = 222   # Band Change info
    freq_len3 = 224   # Band Change info
    freq_len4 = 240   # Band Change info
    freq_len5 = 288   # Band Change info
    freq_len6 = 304   # Band Change info
    freq_len7 = 308   # Band Change info
    if (payload_len == freq_len1 or 
        payload_len == freq_len2 or
        payload_len == freq_len3 or
        payload_len == freq_len4 or
        payload_len == freq_len5 or
        payload_len == freq_len6 or
        payload_len == freq_len7):
        #hexdump(payload)
        np.set_printoptions(formatter={'int':hex})
        #print(payload)
        
        vfoa = get_freq(payload, 0)
        #print("VFO A = ", vfoa)
        
        vfob = get_freq(payload, 1)
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
                    dial_freq = vfoa + offset
                    
                if (vfob >= Freq_table[band_name]['lower_edge'] and
                    vfob <= Freq_table[band_name]['upper_edge'] ):
                    # Found a band match, print out the goods
                    offset = Freq_table[band_name]['offset'] 
                    unselected_vfo = vfob + offset
                    
            print("Band = ", band_name, "  Selected VFO = ", dial_freq, "   unselected VFO = ", unselected_vfo)
            #print("  Lower edge = ", Freq_table[band_name]['lower_edge'] + offset,
            #      "  Upper edge = ", Freq_table[band_name]['upper_edge'] + offset,
            #      "  Offset = ", offset)
            # call GPIO here
            #break


def tcp_sniffer(args):     
    try:
        # can read from piped data input
        #payload = sys.stdin.readline()
        #print(payload)
        
        # filter and capture packets of interest using scapy functions
        a = sniff(
            #filter="tcp and port 50004 and (length == 290 or length == 304 or length == 306 or length == 308)",
            #filter="tcp and port 50004 and (greater 279 and less 310)",
            filter="tcp and port 50004 and greater 279",
            iface=r'eth0',
            prn=parse_packet
            )
                
    except KeyboardInterrupt:
        print('Done', i)


if __name__ == '__main__':
    import sys
    sys.exit(tcp_sniffer(sys.argv))
