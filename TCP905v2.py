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
        self.ptt_state = 0
        self.payload_len = 0
        self.payload_copy = ""
        self.payload_ID = 0
        self.payload_byte2 = 0
        self.__freq_last = 0
        self.__vfoa_band_last = 0
        self.__ptt_state_last = 255 
        self.modeA = 255
        self.filter = 255
        self.datamode = 255
        

    def p_status(self, TAG):
        print("("+TAG+") VFOA Band:", self.vfoa_band,
            " VFOA:", self.selected_vfo, 
            " VFOB = ", self.unselected_vfo, 
            " Split:",self.split_status, 
            " Pre:", self.preamp_status,
            " Att:", self.atten_status,
            " PTT:", self.ptt_state,
            " Mode", self.modeA,
            " Filt:", self.filter,
            " DataM:",self.datamode)
      
                        
    # ID 0x18 00 is 32 bytes and unknown data
    # ID 0x18 01 occurs on band change while tuning or by screen
    # it can also pop up with NMEA data corrupting things
    # has frequency in it same location as d8 message
    # 01 attr in CW mode is mostly zero filled.
    
    # this is a good packet  begions and ends with ths info.  midle is almost all zeros
    #0000  01 18 01 00 00 00 00 00 10 01 34 02 00 00 00 00
    #0110  D3 02 D5 02 8B 00 11 01 0C 01 0C 01 11 01 46 00
        
    def case_x18(self):  # process items in message id # 0x18               
        #if (self.payload_byte2 == 1):
        #hexdump(self.payload_copy)
        #print("(ID:18) Length",self.payload_len)

        if (self.payload_byte2 == 0x01):
            self.atten_status = self.payload_copy[0x011d]
            self.preamp_status = self.payload_copy[0x011c]
            self.modeA = self.payload_copy[0x00bc]
            self.filter = self.payload_copy[0x00bd]
            self.datamode = self.payload_copy[0x00be]
            vfoa = self.get_freq(self.payload_copy, 0) 
            print("(ID:18) Source",format(self.payload_ID, "04x"),
                "Split:",self.split_status,
                "Mode:",self.modeA,
                "Filter:",self.filter,
                "DataM",self.datamode,
                "Raw VFOA = ", vfoa,
                " Length:",self.payload_len)


    # get this message when split is changed, has freq info 
    # process items in message #0xd4 0x00
    # attr = 01 is long and mostly zeros
    def case_xD4(self):    
        #if (self.payload_byte2 > 0):
        #hexdump(self.payload_copy)
        #print("(ID:d4) Length",self.payload_len)
        
        # attr = 0 is he only good one so far.  01 is zeros
        if (self.payload_byte2 == 0):  
            self.split_status = self.payload_copy[0x001b] # message #0xd4 @ 0x0001
            self.modeA = self.payload_copy[0x00bc]
            self.filter = self.payload_copy[0x00bd]
            self.datamode = self.payload_copy[0x00be]
            vfoa = self.get_freq(self.payload_copy, 0) 
            print("(ID:d4) Source",format(self.payload_ID, "04x"),
            "Split:",self.split_status,
            "Mode:",self.modeA,
            "Filter:",self.filter,
            "DataM",self.datamode,
            "Raw VFOA = ", vfoa,
            " Length:",self.payload_len)


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


    def frequency(self):  # 0xd8 0x00 is normal tuning update, 0x18 on band changes
        # toss short packets
        if ((self.payload_ID == 0x18 and self.payload_byte2 == 0x00) or (self.payload_ID == 0xec and self.payload_byte2 == 0x02)):
            return  # 32 byte unknown data
        if (self.payload_len < 0x00b8):  # not long enough likely has wrong data in iti
            return  # can be called for multiple sources, not all good format
        #print("(Freq) Freq from ID:",format(self.payload_ID,"02x"))
        #hexdump(self.payload_copy)
        #print("Length",self.payload_len)
            
        np.set_printoptions(formatter={'int':hex})
        
        # Duplex used split status byte for VFO swap, just has vfoB set different with offset
        # split is updated in message ID 0xD4.  here we can also pick it up and nto wait for 
        # someone to press the split button to generate the d4 event.
        self.split_status  = self.payload_copy[0x001b]
        self.modeA  = self.payload_copy[0x00bc]
        self.filter = self.payload_copy[0x00bd]
        self.datamode = self.payload_copy[0x00be]
        
        # Returns the payload hex converted to int.  
        # This need to have the band offset applied next
        __vfoa = self.get_freq(self.payload_copy, 0) 
        #print("(Freq) VFO A = ", vfoa)
        __vfob = self.get_freq(self.payload_copy, 1)
        #print("(Freq) VFO B = ", vfob)

        # Look for band changes
        if (__vfoa != self.__freq_last):
            # Search the Freq_table to see what band these values lie in
            for __band_name in Freq_table:
                if (__vfoa >= Freq_table[__band_name]['lower_edge'] and
                    __vfoa <= Freq_table[__band_name]['upper_edge'] ):
                    # Found a band match, print out the goods
                    self.__offset = Freq_table[__band_name]['offset'] 
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
            if (self.vfoa_band != self.__vfoa_band_last):
                self.band_io_output(self.vfoa_band)
                self.__vfoa_band_last = self.vfoa_band
            
            self.__freq_last = __vfoa
        else:
            print("(Freq)  Source",format(self.payload_ID, "04x"),
                "Split:",self.split_status,
                "Mode:",self.modeA,
                "Filter:",self.filter,
                "DataM",self.datamode,
                "Raw VFOA = ",__vfoa,
                " Length:",self.payload_len)
        
        return self.vfoa_band
      
        
    # When spectrum is enabled AND there is noise+signal > ref line
    #   dump spectrum data in 0xe8001
    #  bytes 0000-0011 never change spectrum starts a 0x0012
    def spectrum(self):
        #hexdump(s"(spectrum)"elf.payload_copy)   
        pass
      
      
    # 0x2c 0x00 - get at start of PTT and occaionally in RX
    # 0x2c 0x01 - get at most(but not all) mode changes.  Some are skipped.
    #      at pos 0x08 always = 0x24
    #      attr byte 8   byte 9   byte A  byte B   byte bd
    #      0x01 24       0x01     44      00       4 = RTTY   FM,SSB mode, mo msg for cw
    #      0x01 24       0x01     44      00       1 = USB   
    #      0x01 24       0x01     44      00       7 = FM   
    #      0x01 24       0x01     44      00       8 = DV then
    #           24         01     c0      02    in DV and often repeats and has gps data in place of frequency and mode, still 308 long
    #   0 is LSB
    #   2 is cw
    #   6 is AM
    def mode(self): # not likely the real mode change as only some issue this message
        #  must be some other primary event
        if (self.payload_byte2 == 1):  # 1 - = mode change, 0 has GPS data.
            self.modeA  = self.payload_copy[0x00bc]
            self.filter = self.payload_copy[0x00bd]
            self.datamode = self.payload_copy[0x00be]
            __vfoa = self.get_freq(self.payload_copy, 0) 
            print("(mode)  Source",format(self.payload_ID, "04x"),
            "Split:",self.split_status,
            "Mode:",self.modeA,
            "Filter:",self.filter,
            "DataM",self.datamode,
            "Raw VFOA = ", __vfoa,
            " Length:",self.payload_len)
        
    def ptt_start(self):
        #print("(ptt_start) PTT start event?? Likely not ")
        pass
       
        
    # PTT sequence 
    # 0xe8-00 - see Github Wiki pages for examples of mesaage ID flow
    # 0xe8-01 is spectrum data 
    def ptt(self): 
        if (self.payload_byte2 == 1):  # spectrum data
            self.spectrum()
        # watch for PTT value changes
        if (self.vfoa_band != ""):   # block PTT until we know what band we are on
            if (self.payload_byte2 == 0):  # value 1 has no recognizable PTT or freq data
                self.ptt_state = self.payload_copy[0x00ef]
                #print("PTT state = ", self.ptt_state)
                if (self.ptt_state != self.__ptt_state_last):
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
                    self.__ptt_state_last = self.ptt_state


    def TX_on(self):
        print("(Tx_on) Transmitting... - sometimes not")
        hexdump(self.payload_copy)
        print("(dump) Length:", self.payload_len)
        

    def dump(self):
        hexdump(self.payload_copy)
        print("(dump) Length:", self.payload_len)


    def unhandled(self):
        return "unhandled message"


    def case_default(self):
        #hexdump(payload_copy)
        __payload_len = len(self.payload_copy)
        print("(case_default) Unknown message,ID:0x"+format(self.payload_ID,'02x')+"  Attr:0x"+format(self.payload_byte2, '02x')+"  Length:", __payload_len)
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
            # These are IDs I have examined and a few are (reasonably) known.
            # A lot are marked with NMEA in the payload.. IT seems way too much to be intentional
            # I would make a guess that parts of these payloads are not used and have buffer 
            #    data left over from earlier and different packets.
            case 0x00: self.unhandled(),  # 0x00 01 - 264 bytes in DV mode next to 04 packets spectrum likely
            case 0x04: self.unhandled(),  # 0x04-01 - 268 byte in DV mode, was all zeros
            case 0x08: self.mode(),       # 0x08-01 - 272 byte payload, show up on mode change around DV mode has freq, mode, filt all 
                                          # 0x08 03 - 784 byte spectrum       on 2M and other bands SSB
            case 0x0b: self.dump(),       # 0x0b xx - ??
            case 0x0c: self.dump(),self.mode(),  # 0x0c 00 - 20 byte unknown data, not freq, lots of them saw at satartup while in DV/FM mode
            case 0x10: self.unhandled(),  # 0x10 03 - 792 byte spectrum maybe
            case 0x14: self.unhandled(),  # 0x14 01 - 284 byte spectrum maybe
                                          # 0x14 03 - 796 byte unknown data, not freq, lots of them
            case 0x18: self.case_x18(),self.frequency(),   # 0x18-01 - 288 bytes for band chg, preamp, atten, likely more
                                          # 0x18 00 - 32 bytes continuous  unknown data
                                          # 0x18 03 - 800 bytes lots of 0s adn some GPS near end.  Surrounded by 30, 40, a d0, then 54 an 64 IDs. Was in DV/FM
            case 0x1c: self.unhandled(),  # 0x1c 00 - 0x23 bytes NMEA has oocasional $GPGGA, slows or stops when squelch is open on good signal
            case 0x20: self.dump(),       # 0x20 xx - ??
            case 0x24: self.mode(),       # 0x24 00 - 88 bytes NMEA data, slow intermittent
                                          # 0x24 01 - 300 bytes  get on filter change.  Has freq, mode, filt etc
            case 0x28: self.mode(),       # 0x28 01 - 304 bytes  get on filt change in SSB mode, mode changes to RTTY,  has freq, mode and all.
            case 0x2c: self.mode(),self.frequency(),  # 0x2c 00 - 52 bytes follows PTT.  unknown data  NMEA during RX. 
                                          # 0x2c 01 - 308 bytes get on mode change, has frequency data in it both vfos
            case 0x30: self.unhandled(),  # 0x30 01 - 312 bytes NMEA data
                                          # 0x30 03 - NMEA data
            case 0x34: self.unhandled(),  # 0x34 00 - 0x13 bytes $GNZDA NMEA data, usually 0s
            case 0x38: self.unhandled(),  # 0x38 00 - 64 bytes NMEA data,like $GNZDA  mostly 0s, msg rate speeds up in TX
            case 0x3c: self.unhandled(),  # 0x3c 00 - 68 bytes NMEA, $GPGGA, $GNZDA, $GLGSV  Fast rate during TX
            case 0x40: self.unhandled(),  # 0x40 00 - 72 bytes NMEA data. On PTT and on band change
            case 0x44: self.unhandled(),  # 0x44 00 - 0x4b bytes NMEA data shows on startup of radio
                                          # 0x44 03 - 844 bytes Looks like spectrum data, was in RTTY switched to AM and 23cm to RTTY could be initial screen draw as happens on band change
            case 0x48: self.unhandled(),  # 0x48 03 - 848 bytes  Unknkown, was in FM and DV\FM, issued on switch from DV to SSB and back to DV
            case 0x4c: self.unhandled(),       # 0x4c 01 - 356 bytes was in DV/FM all 0s   Spectrum in AM mode  Can visualize teh APRS bursts in the middle of the data range.
                                          #  when spectrum ref is lowered, data becomes 0s and then stops.  Only strong sugs burst packets
                                          # 0x4c 02 - 596 bytes  USB 2.4G  all zero quiet band
                                          # 0x4c 03 - 852 bytes  DV\FM, likely spectrum
            case 0x50: self.unhandled(),  # 0x50 00 - 88 bytes NMEA data
                                          # 0x50 03 - 856 bytes 1 time on TX start, lots of 0 ending with NMEA data
            case 0x54: self.unhandled(),  # 0x54 01 - 348 bytes NMEA data in DV/FM mode
            case 0x58: self.unhandled(),  # 0x58 02 - 608 bytes was in FM and SSB spectrum likely
            case 0x5c: self.unhandled(),  # 0x5c 01 - 356 bytes was in DV/FM all 0s
                                          # 0x5c 02 - 612 bytes in AM mode, looks like spectrum
            case 0x60: self.unhandled(),  # 0x60 00 - 104 bytes NMEA data
            case 0x64: self.unhandled(),  # 0x64 00 - 108 bytes NMEA data
                                          # 0x64 01 - 364 bytes NMEA data - burst of packets
                                          # 0x64 02 - 620 bytes NMEA data - burst of packets
            case 0x68: self.unhandled(),  # 0x68 00 - 112 bytes NMEA data.Zeros in DV/FM
                                          # 0x68 02 - 624 bytes ?? 
            case 0x6c: self.unhandled(),  # 0x6c 00 - 116 bytes NMEA data
                                          # 0x6c 01 - 372 bytes ?? 
            case 0x70: self.unhandled(),  # 0x70 00 - 120 bytes NMEA on RX, 0s on TX
            case 0x74: self.unhandled(),  # 0x74 00 - 124 bytes ??
            case 0x78: self.unhandled(),  # 0x78 00 - 128 bytes NMEA data 
            case 0x7c: self.unhandled(),  # 0x7c 00 - 132 bytes NMEA data
            case 0x80: self.unhandled(),  # 0x80 00 - NMEA data
            case 0x84: self.dump(),       # 0x84 xx - ?? bytes ??
            case 0x88: self.unhandled(),  # 0x88 00 - 144 bytes mostly 0s
            case 0x8c: self.dump(),       # 0x8c xx - ?? bytes ??
            case 0x90: self.unhandled(),  # 0x90 01 - 408 bytes spectrum on 2.4G
            case 0x94: self.unhandled(),  # 0x94 01 - 412 bytes Looks like spectrum on 2.4G SSB
                                          # 0x94 02 - 668 bytes Looks like spectrum
            case 0x98: self.dump(),       # 0x98 xx - ?? bytes ??
            case 0x9c: self.unhandled(),  # 0x9c 00 - 164 bytes saw in DV/FM. nearly all zeros,  rare message.  
            case 0xa0: self.unhandled(),  # 0xa0 02 - 680 bytes Spectrum likely in AM 
            case 0xa4: self.unhandled(),  # 0xa4 00 - 172 bytes shows in DV/FM mode. Looks like GPS data.  Codl just be gps mixed in
                                          # 0xa4 01 - 428 bytes shows in DV/FM mode. All 0s 
            case 0xa8: self.unhandled(),  # 0xa8 00 - 176 bytes 2.4G all zeros no signal
                                          # 0xa8 01 - 488 and 432 bytes shows in DV/FM when ref level rasdised and APRS signal and on 2.4G
                                          # 0xa8 03 - 944 bytes shows in FM afer a readio restart
            case 0xac: self.dump(),       # 0xac xx - ?? bytes ??
            case 0xb0: self.unhandled(),  # 0xbo 03 - 952 bytes shows on radio startup, mostly zero filled
            case 0xb4: self.dump(),       # 0xb4 01 - 444 bytes  spectrum on 2.4G SSB
                                          # 0xb4 02 - 700 bytes  spectrum maybe on 2M FM after startup
            case 0xb8: self.dump(),       # 0xb8 01 - 448 bytes  3.4G band SSB all zeros quiet band
            case 0xbc: self.dump(),       # 0xbc 01 - xx bytes  was in DV/FM lots of zeros with some data
            case 0xc0: self.unhandled(),  # 0xc0 01 - 488 bytes  was in DV/FM msotly 0s nmea data
                                          # 0xc0 02 - xx bytes  was in DV/FM msotly 0s nmea data
            case 0xc4: self.unhandled(),  # 0xc4 00 - 204 bytes  RTTY spectrum/GPS maybe
                                          # 0xc4 02 - 716 bytes  was in DV/FM mostl;y 0s, some nmea
            case 0xc8: self.unhandled(),  # 0xc8 00 - 208 bytes  RTTY on 23cm spectrum maybe
                                          # 0xc8 01 - 464 bytes  was in DV/FM mosty all zeros, maybe spectrum
            case 0xcc: self.dump(),       # 0xcc 01 - 468 bytes  was in DV/FM  had ref lvl down
            case 0xd0: self.ptt_start(),  # 0xd0 00 - 216 bytes PTT start event, freq at 0xb8 for current VFO.  Works on simplex, duplex, no split, no VFOb data
            case 0xd4: self.case_xD4(), self.frequency(), # 220 bytes get Split msg on d4-00
                                          # 0xd4 01 - 476 bytes Mostly zeros, came after a PTT event
            case 0xd8: self.frequency(),  # 0xd8 00 - 224 bytes comes in 2 lengths, one short and one with NMEA data added on.
            case 0xdc: self.unhandled(),  # 0xdc 00 - 228 bytes rarely shows, has NMEA data in it showed when ref level raised on 2.4G
            case 0xe0: self.unhandled(),  # 0xE0 01 - 488 bytes in FM spectrum on band change to 23cm
                                          # 0xE0 02 - 744 bytes in DV/FM spectgrum+GPS data
            case 0xe4: self.unhandled(),  # 0xe4 01 - 492 bytes shows when activity on spectrum wasin DV
            #e8 00 is PTT transition
            #e8 01 is spectrum data on RX when enabled 0
            #set screen to meter mode or signal+noise drop < ref line, get 1 with all 0 then no more until signal resumes
            case 0xe8: self.ptt(),        # 0xe8 00 tx/rx changover trigger, e801 normal RX or TX state.  PTT is last byte but may be in others also. Byte 0xef is PTT state
            case 0xec: self.frequency(),  # 0xec 00 - 244 bytes occurs on data-mode (digital mode) change
                                          # 0xec 02 - 0x133 bytes filled with zeros and blocks of gps data
            #the 04, 54, 64 f4, fc ID showed up when there was a signal in DV/FM listeing to packet.  Filled with 0s.  WIl lalso show up when a singal is off freq
            case 0xf0: self.unhandled(),  # 0xf0 00 - 248 bytes was in DV mode. Looks like spectrum.  had squelch on in FM
                                          # 0xf0 01 - 504 bytes was in DV mode. Looks like spectrum.  had squelch on in FM
                                          # 0xf0 02 - ??bytes was in DV mode.
            case 0xf4: self.unhandled(),  # 0xf4 00 - 252 bytes NMEA data shows up when a large signal was on teh spectgrum and the ref line was < 0 which squelces f4 02 in DV mode.
                                          # 0xf4 02 - 764 bytes NMEA data at end, looks like spectrum in DV mode.  Stops when ref line <0
            case 0xf8: self.unhandled(),  # 0xf8 00 - 255 bytes shows up periodically in middle of TX streams and other times
            case 0xfc: self.unhandled(),  # 0xfc 00 - 260 bytes Lookjs like spectrum/NMEA data.  Saw in many palces, during TX, in FM to SSB transition, DV/FM            
            
            case _: self.case_default()   # anything we have not seen yet comes to here

    def switch_case(self, payload, payload_len):
        self.payload_copy = payload
        self.payload_ID = payload[0x0001]
        self.payload_byte2 = payload[0x0002]
        self.payload_len = payload_len 
        
        # Turn off all lines below this to see only hex data on screen
        #if (self.payload_ID == 0xa4):   # a0 a4 a8 ac
         #   hexdump(payload)
         #   print(self.payload_len, "\n")
        
        # Turn this print ON to see all message IDs passing through here
        #print("Switch on 0x"+format(self.payload_ID,"02x")+"  Attr:0x"+format(self.payload_byte2,"02x")+"  Len:", format(self.payload_len))
        
        #Turn this on to only see hex dumps for any and all packets
        #self.dump()
        
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
            mh.switch_case(payload, payload_len )  # this extracts and routes messages to functions


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
