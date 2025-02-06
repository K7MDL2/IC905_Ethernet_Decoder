#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  TCP905v2.py  
#  
#  Feb 2025 K7MDL
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
    
    
#  __________________________________________________________________
#    
#  GPIO outputs for Band and PTT
#  __________________________________________________________________
#
    
class OutputHandler:     

    def ptt_io_output(self, band, ptt):
        print("PTT GPIO action here for", band, "PTT state", ptt)
        
        
    def band_io_output(self, band):
        print("BAND GPIO action here for", band)


#  __________________________________________________________________
#    
#  Packet data processing functions
#  __________________________________________________________________
#

class BandDecoder(OutputHandler):
# We are inheriting from OutputHandler class so we can access its functions 
#   and variables as if they were our own.
    def __init__(self):
        self.vfoa_band = ""
        self.vfob_band = ""
        self.selected_vfo = 0
        self.unselected_vfo = 0
        self.__selected_vfo_split_Tx = 0
        self.__offset = 0
        self.__vfoa_band_split_Tx = 0
        self.split_status = 0
        self.preamp_status = 0
        self.atten_status = 0
        self.ptt_state = -1
        self.payload_copy = ""
        self.payload_ID = 0
        self.payload_byte2 = 0


    def p_status(self, TAG):
        print("("+TAG+") VFOA Band:", self.vfoa_band, " VFOA:", self.selected_vfo, " VFOB = ", self.unselected_vfo, 
            " Split:",self.split_status, " Pre:",self.preamp_status, " Att:", self.atten_status, " PTT:", self.ptt_state)
      
                        
    def case_x18(self):  # process items in message id # 0x18        
        #print("Preamp  len", len(self.payload_copy), "  extra byte", self.payload_byte2)
        #hexdump(self.payload_copy)
        if (self.payload_byte2 == 1):
            if (self.payload_copy[0x011d] == 1):
                self.atten_status = 1
            else:
                self.atten_status = 0

            if (self.payload_copy[0x011c] == 1):
                self.preamp_status = 1
            else: 
                self.preamp_status = 0


    def case_xD4(self):    # process items in message #0xd4
        if (self.payload_copy[0x001b] == 1): # message #0xd4 @ 0x0001
            self.split_status = 1
        else:
            self.split_status = 0


    # convert little endian bytes to int frequency 
    def get_freq(self, payload, VFO):
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


    def frequency(self):
        __freq_last = 0
        __vfoa_band_last = 0
        #band_name = ""
        
        #hexdump(self.payload_copy)
        np.set_printoptions(formatter={'int':hex})
        #print(self.payload_copy)
        
        # Duplex used split status byte for VFO swap, just has vfoB set different with offset
        # split is updated in message ID 0xD4.  here we can also pick it up and nto wait for 
        # someone to press the split button to generate the d4 event.
        self.split_status  = self.payload_copy[0x001b]
        
        # Returns the payload hex converted to int.  
        # This need to have the band offset applied next
        __vfoa = self.get_freq(self.payload_copy, 0) 
        #print("VFO A = ", vfoa)
        __vfob = self.get_freq(self.payload_copy, 1)
        #print("VFO B = ", vfob)

        # Look for band changes
        if (__vfoa != __freq_last):
            # Search the Freq_table to see what band these values lie in
            for __band_name in Freq_table:
                if (__vfoa >= Freq_table[__band_name]['lower_edge'] and
                    __vfoa <= Freq_table[__band_name]['upper_edge'] ):
                    # Found a band match, print out the goods
                    self.offset = Freq_table[__band_name]['offset'] 
                    self.selected_vfo = __vfoa + self.__offset
                    self.vfoa_band = __band_name
                    
                if (__vfob >= Freq_table[__band_name]['lower_edge'] and
                    __vfob <= Freq_table[__band_name]['upper_edge'] ):
                    # Found a band match, print out the goods
                    self.__offset = Freq_table[__band_name]['offset'] 
                    self.unselected_vfo = __vfob + self.__offset
                    self.vfob_band = __band_name

            self.p_status("TUN") # print out our state
            #print("  Lower edge = ", Freq_table[self.vfoa_band]['lower_edge'] + self.__offset,
            #      "  Upper edge = ", Freq_table[self.vfoa_band]['upper_edge'] + self.__offset,
            #      "  Offset = ", self.__offset)
            
            #  set band outputs on band changes
            if (self.vfoa_band != __vfoa_band_last):
                self.band_io_output(self.vfoa_band)
                __vfoa_band_last = self.vfoa_band
            
            __freq_last = __vfoa
        
        return self.vfoa_band
      
        
    # PTT sequence  - see Github Wiki pages for examples of mesaage ID flow
    def ptt(self):
        __ptt_state_last = 255       
        # watch for PTT value changes
        if (self.vfoa_band != ""):   # block PTT until we know what band we are on
            if (not self.payload_byte2):
                self.ptt_state = self.payload_copy[0xef]
                #print("PTT state = ", self.ptt_state)
                if (self.ptt_state != __ptt_state_last):
                    if (self.ptt_state == 1):  # do not TX if the band is still unknown (such as at startup)
                        #print("VFO A Band = ", self.vfoa_band, " ptt_state is TX ", self.ptt_state, " Msg ID ", hex(self.payload_copy[0x0001]))
                        if (self.split_status == 1): # swap selected and unselected when split is on during TX
                            self.__vfoa_band_split_Tx = self.vfoa_band  # back up the original VFOa band
                            self.__selected_vfo_split_Tx = self.selected_vfo  # back up original VFOa
                            self.selected_vfo = self.unselected_vfo  # during TX assign b to a
                            self.vfoa_band = self.vfob_band
                    if (self.ptt_state == 0):
                        #print("VFO A Band = ", self.vfoa_band, " ptt_state is RX ", self.ptt_state, " Msg ID ", hex(self.payload_copy[0x0001]))
                        if (self.split_status == 1): # swap selected and unselected when split is on during TX
                            self.vfoa_band = self.__vfoa_band_split_Tx
                            self.selected_vfo = self.__selected_vfo_split_Tx
                    
                    self.p_status("PTT")
                    self.ptt_io_output(self.vfoa_band, self.ptt_state)
                    __ptt_state_last = self.ptt_state


    def TX_on(self):
        print("Transmitting...")


    def dump(self):
        hexdump(self.payload_copy)


    def unhandled(self):
        return "unhandled message"


    def case_default(self):
        #hexdump(payload_copy)
        __payload_len = len(self.payload_copy)
        print("Unknown message,ID:0x"+format(self.payload_ID,'02x')+"  Attr:0x"+format(self.payload_byte2, '02x')+"  Length:", __payload_len)
        return "no match found"

#
#   End of class BandDecoder
#

#  __________________________________________________________________
#    
#   Routing to functions based on Message ID
#  __________________________________________________________________
#

class Message_handler(BandDecoder):
    # We are inheriting from BandDecoder class so we can access its functions 
    #   and variables as if they were our own.
        
    # These is a list of observed message IDs.  
    # Turn on print in the switch_case() method to see all IDs routed through to this list
    # unhandled does nothing, squelches the known messages so we can see unknown messages easier
    # Replace any of these with dump() to do a hexdump and help identify what it does.
    # Lower the packet length filter size and you will see many more. Unclear if they need to be looked at.
    
    def switch(self, ID):
        match ID:
            #case 0xYY: dump,  # example of a message routed to hex dump function for investigation
            
            # These are the (reasonably) known IDs.
            case 0xd4: self.case_xD4(),   # Split
            case 0xd8: self.frequency(),  # D8 00 - comes in 2 lengths, one short and one with NMEA data added on.
            case 0xe8: self.ptt(),        # e8 00 tx/rx changover trigger, e801 normal RX or TX state.  PTT is last byte but may be in others also. Byte 0xef is PTT state
            case 0xfc: self.TX_on(),      # fc 00 heartbeat message during TX
            case 0x18: self.case_x18(),   # preamp and atten, likely more
            case 0xf8: self.TX_on(),      # f8 00 shows up periodically in middle of fc00 TX streams
            case 0x30: self.unhandled(),  # 0x3003 is NMEA data
            
            # When these are figured out, move them off this list and put them above.
            case 0x10 | 0x14  | 0x1c: self.unhandled(),
            case 0x20 | 0x24 | 0x28 | 0x2c: self.unhandled(),
            case 0x34 | 0x3c: self.unhandled(),
            case 0x40 | 0x48 | 0x4c: self.unhandled(),
            case 0x50 | 0x54 | 0x58 | 0x5c: self.unhandled(),
            case 0x60 | 0x64 | 0x68: self.unhandled(),
            case 0x90: self.unhandled(),
            case 0xb4 | 0xb8 | 0xbc: self.unhandled(),
            case 0xc0 | 0xc4 | 0xc8 | 0xcc: self.unhandled(),
            case 0xd0 | 0xdc: self.unhandled(),
            case 0xe0 | 0xe4: self.unhandled(),
            case 0xf0 | 0xf4: self.unhandled()
            case _: self.case_default()

    def switch_case(self, payload):
        self.payload_copy = payload
        self.payload_ID = payload[0x0001]
        self.payload_byte2 = payload[0x0002]
        # Turn this print ON to see all message IDs passing theough here
        #print("Switch on ",hex(self.payload_ID))
        self.switch(self.payload_ID)
        
#  __________________________________________________________________
#    
#   Packet Capture and Filtering
#  __________________________________________________________________
#

def parse_packet(packet):
    conf.verb = 0
    
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
            mh.switch_case(payload)  # this extracts and routes messages to functions


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
            prn=parse_packet  # call this function to process filtered packets
            )
                
    except KeyboardInterrupt:
        print('Done', i)


if __name__ == '__main__':
    import sys
    io = OutputHandler()  # instantiate our classes
    bd = BandDecoder()
    mh = Message_handler()
    sys.exit(tcp_sniffer(sys.argv))
