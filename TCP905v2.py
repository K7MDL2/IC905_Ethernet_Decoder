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
from time import sleep
import RPi.GPIO as GPIO


#  Freq_table:
#  These band edge frequency values are based on the radio message VFO
#    values which have no offset applied
#  We use this value then once we know the band we can add the
#    fixed offset and then display the actual dial frequency

#  The 10G band values in this table are just dummy values until
#    the 10G transverter is hooked up to observe the actual values

# The band and ptt values are the mapping to the group of
#    6 pins for band and 6 pins for ptt
#    Set the pin value(s) = 1 that you want activated when the band is active
#    There is an inversion flag to corert for buffer inversions

# At startup all pins will be set to 0 then initialized once the band
#    is first determined.

# For BCD output to the Remote BCD Decoder board, edit the band
#    values = 0 through 5 so only using 3 io pins
#    and ptt values will all be set to 1 using only 1 io pin
# Example values for BCD decoder
#   2M decimal   0 or in binary format 0b0000000
#   70cm decimal 1 or in binary format 0b0000001
#   23cm decimal 2 or in binary format 0b0000010
#   13cm decimal 3 or in binary format 0b0000011
#    6cm decimal 4 or in binary format 0b0000100
#    3cm decimal 5 or in binary format 0b0000101
# Set all bands ptt to decimal 1 or in binary format 0b0000001

# thsi is set up for 3 wire BCD + 1 wire PTT for the Remote Decdoer board
Freq_table = { '2M': {
                    'lower_edge':144000000,
                    'upper_edge':148000000,
                        'offset':0,
                          'band':0b00000000,
                           'ptt':0b00000001,
                },
                '70cm': {
                    'lower_edge':231000000,
                    'upper_edge':251000000,
                        'offset':199000000,
                          'band':0b00000001,
                           'ptt':0b00000001,
                },
                '23cm': {
                    'lower_edge':351000000,
                    'upper_edge':411000000,
                        'offset':889000000,
                          'band':0b00000010,
                           'ptt':0b00000001,
                },
                '13cm': {
                    'lower_edge':562000000,
                    'upper_edge':712000000,
                        'offset':1738000000,
                          'band':0b00000011,
                           'ptt':0b00000001,
                },
                '6cm': {
                    'lower_edge':963000000,
                    'upper_edge':1238000000,
                        'offset':4687000000,
                          'band':0b00000100,
                           'ptt':0b00000001,
                },
                '3cm': {
                    'lower_edge':2231000000,
                    'upper_edge':2251000000,
                        'offset':99989000000,
                          'band':0b00000101,
                           'ptt':0b00000001,
                }
            }

# IO-Table:
# These are the GPIO pin assignments of BAND and PTT outputs.
# 1 or more pins may be assigned to any band so they are not band specific.
# The band and ptt keys in the Freq_table map the bank of pins to a band

# We use up to 6 pins for band output and up to 6 for PTT
# BCD mode will use fewer pins and the extras will be ignored
# set the inversion this to match your hardware.  Buffering usually inverts the logic

# The 3 relay HAT I have uses pin CH1=26  CH2=20  CH3=21 (25, , 28, 29 using Wiring Pi numbers on the board

# This is set up for  3-wire BCD Band and 1-wire PTT for the Remote BCD DEcdoer board
IO_table = {
                 0x01 : {
                      'band_pin':4,
                   'band_invert':True,
                       'ptt_pin':17,
                    'ptt_invert':True,
                 },
                 0x02 : {
                      'band_pin':3,
                   'band_invert':True,
                       'ptt_pin':0,
                    'ptt_invert':True,
                 },
                 0x04 : {
                      'band_pin':2,
                   'band_invert':True,
                       'ptt_pin':0,
                    'ptt_invert':True,
                 },
                 0x08 : {
                      'band_pin':0,
                   'band_invert':True,
                       'ptt_pin':0,
                    'ptt_invert':True,
                 },
                 0x10: {
                      'band_pin':0,
                   'band_invert':True,
                       'ptt_pin':0,
                    'ptt_invert':True,
                 },
                 0x20 : {
                      'band_pin':0,
                   'band_invert':True,
                       'ptt_pin':0,
                    'ptt_invert':True,
                }
            }

#
#  __________________________________________________________________
#
#  GPIO outputs for Band and PTT
#  __________________________________________________________________
#

class OutputHandler:

    def gpio_config(self):
        GPIO.setmode(GPIO.BCM)
        for i in IO_table:
            band_pin = IO_table[i]['band_pin']
            band_invert =  IO_table[i]['band_invert']
            ptt_pin = IO_table[i]['ptt_pin']
            ptt_invert = IO_table[i]['ptt_invert']
            print("i=", format(i, '06b'), "band_pin:", band_pin, " ptt_pin", ptt_pin)
            GPIO.setup(band_pin, GPIO.OUT, initial=band_invert)
            GPIO.setup(ptt_pin,  GPIO.OUT, initial=ptt_invert)
        print("GPIO pin mode setup complete")


    def ptt_io_output(self, band, ptt):
        for __band_name in Freq_table:
            if (__band_name == band):
                band_pattern = Freq_table[__band_name]['ptt']
                # Found a band match, set ptt io pin(s)
                if ptt:
                    p = bd.colored(255,0,0,"(+TX++)")
                else:
                    p = bd.colored(45,255,95,"(-RX--)")

                b = bd.colored(255,235,145, format(str(band),"5"))
                bp = bd.colored(0,255,255, format(band_pattern,'06b'))
                print(p+" Output for "+b+" Pattern:"+bp)

                if (ptt):
                    ptt = 0xff
                else:
                    ptt = 0x00

                for __pins in IO_table:
                    pin_invert = IO_table[__pins]['ptt_invert']
                    io_pin     = IO_table[__pins]['ptt_pin']
                    pin_state  = (band_pattern & __pins & ptt)

                    pin_state = bool(pin_state)   # convert decimal number to a boolean value

                    if pin_invert:
                        pin_state = pin_state ^ 1 # invert the pin
                        #print("pin state after inversion:", int(pin_state))

                    #print("index", __pins, "pin state:", pin_state,"on",io_pin, "inverted", pin_invert)

                    GPIO.output(io_pin, pin_state)  # set our pin



    def band_io_output(self, band):
        # turn on selected band output
        for __band_name in Freq_table:
            if (__band_name == band):
                band_pattern = Freq_table[__band_name]['band']
                # Found a band match, now loop through the set of IO pins
                t = bd.colored(235,110,200, "(BAND )")
                b = bd.colored(255,225,145, format(str(band),"5"))
                p = bd.colored(0,255,255, format(band_pattern,'06b'))
                print(t+" Output for "+b+" Pattern:"+p)
                template = 0x0000

                for __pins in IO_table:
                    pin_invert = IO_table[__pins]['band_invert']
                    io_pin     = IO_table[__pins]['band_pin']
                    pin_state  = (band_pattern & __pins)

                    if pin_state:
                        pin_state = 1
                    else:
                        pin_state = 0

                    if pin_invert:
                        pin_state = pin_state ^ 1 # invert the pin
                        #print("pin state after inversion:", int(pin_state))

                    #print("index", __pins, "pin state:", pin_state,"on",io_pin, "inverted", pin_invert)
                    GPIO.output(io_pin, pin_state)

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
        self.payload_ID_byte = 0
        self.payload_Attrib_byte = 0
        self.__freq_last = 0
        self.__vfoa_band_last = 0
        self.__ptt_state_last = 255
        self.modeA = 255
        self.filter = 255
        self.datamode = 255
        self.in_menu = 0
        self.PTT_hang_time = 0.3


    def check_msg_valid(self):
        if (self.payload_ID != 0xa803):
            if (self.payload_copy[0x000a] != 0x44 and
                self.payload_copy[0x000b] != 0x00):
                #print("Rejected message from ID", format(self.payload_ID, "04x"))
                return  1 # get avoid garbage versions
            else:
                #print("Accepted message from ID", format(self.payload_ID, "04x"))
                return 0   # return 1 for bad, 0 for good


    def p_status(self, TAG):

        print(bd.colored(155,180,200,"("+TAG+")"),
            " VFOA Band:"+bd.colored(255,225,165,format(self.vfoa_band,"4")),
            " A:"+bd.colored(255,255,255,format(self.selected_vfo, "11")),
            " B:"+bd.colored(215,215,215,format(self.unselected_vfo, "11")),
            " Split:"+bd.colored(225,255,90,format(self.split_status, "1")),
            " M:"+format(self.modeA, "1"),
            " F:"+format(self.filter, "1"),
            " D:"+format(self.datamode, "1"),
            " P:"+format(self.preamp_status, "1"),
            " A:"+format(self.atten_status, "1"),
            " PTT:"+bd.colored(115,195,110,format(self.ptt_state, "1")),
            #" Menu:"+format(self.in_menu, "1"),   #  this toggles 0/1 when in menus,and.or when there is spectrum flowing not sure which
            " Src:0x"+format(self.payload_ID, "04x"))


    # If we see corrupt values then look at the source.
    # Some messages are overloaded - meaning they can have radio
    #   status or have other spectrum like data in the same length
    #   and ID+Attrib combo/   Calling check_msg_valid to filter out
    #   bad stuff based on observed first row byte patterns

    def case_x18(self):  # process items in message id # 0x18
        #hexdump(self.payload_copy)
        #print("(ID:18) Length",self.payload_len)

        if self.check_msg_valid():
            return

        self.split_status = self.payload_copy[0x001b] # message #0xd400 @ 0x0001
        # There is no preamp or atten on bands above 23cm
        if (self.vfoa_band == "13cm" or self.vfoa_band == "6cm"):
            self.atten_status = 0
            self.preamp_status = 0
        else:
            self.atten_status = self.payload_copy[0x011d]
            self.preamp_status = self.payload_copy[0x011c]
        self.modeA = self.payload_copy[0x00bc]
        self.filter = self.payload_copy[0x00bd]+1
        self.datamode = self.payload_copy[0x00be]
        self.in_menu = self.payload_copy[0x00d8]
        self.frequency()
        #self.p_status("ID:18") # print out our state


    # get this message when split is changed
    #  x18 has the status
    # process items in message #0xd4 0x00
    # attr = 01 is long and mostly zeros
    # d400 can be filled with other type data on some occasions, maybe band specific, not sure.
    def case_xD4(self):
        #hexdump(self.payload_copy)
        #print("(ID:D4) Length",self.payload_len)

        if self.check_msg_valid():
            return

        self.split_status = self.payload_copy[0x001b] # message #0xd400 @ 0x0001
        #self.split_status = self.payload_copy[0x00b3] # message #0xd400 @ 0x0001
        self.modeA = self.payload_copy[0x00bc]
        self.filter = self.payload_copy[0x00bd]+1
        self.datamode = self.payload_copy[0x00be]
        self.in_menu = self.payload_copy[0x00d8]
        self.frequency()
        #self.p_status("ID:D4") # print out our state


    # convert little endian bytes to int frequency
    # vfo is the starting address for desired in the payload
    def get_freq(self, payload, vfo):
        freq_hex_dec = np.array([0, 0, 0, 0],dtype=np.uint8)

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
        #print("(Freq) Freq from ID:",format(self.payload_ID,"02x"))
        #hexdump(self.payload_copy)
        #print("Length",self.payload_len)

        if self.check_msg_valid():
            return

        # Duplex used split status byte for VFO swap, just has vfoB set different with offset
        # split is updated in message ID 0xD4.  Here we can also pick it up and not wait for 
        # someone to press the split button to generate the d4 event.
        if (self.payload_ID == 0xa803):   # from startup message, different byte locations
            vfoa = 0x00fc
            vfob = 0x0108
            self.split_status  = self.payload_copy[0x005f]
            self.preamp_status = self.payload_copy[0x0160]
            self.atten_status = self.payload_copy[0x0161]
        else:  # from anyother message ID that call here
            vfoa = 0x00b8
            vfob = 0x00c4
            self.split_status  = self.payload_copy[0x001b]
            # collect premp and atten via other messages.

        self.modeA  = self.payload_copy[vfoa+4]
        self.filter = self.payload_copy[vfoa+5]+1
        self.datamode = self.payload_copy[vfoa+6]

        if (self.vfoa_band == "13cm" or self.vfoa_band == "6cm"):
            self.atten_status = 0
            self.preamp_status = 0

        np.set_printoptions(formatter={'int':hex})

        # Returns the payload hex converted to int.
        # This need to have the band offset applied next
        __vfoa = self.get_freq(self.payload_copy, vfoa)
        #print("(Freq) VFO A = ", vfoa)
        __vfob = self.get_freq(self.payload_copy, vfob)
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

            self.p_status("FREQ ") # print out our state
            #print("  Lower edge = ", Freq_table[self.vfoa_band]['lower_edge'] + self.__offset,
            #      "  Upper edge = ", Freq_table[self.vfoa_band]['upper_edge'] + self.__offset,
            #      "  Offset = ", self.__offset)

            #  set band outputs on band changes
            if (self.vfoa_band != self.__vfoa_band_last):
                self.band_io_output(self.vfoa_band)
                self.__vfoa_band_last = self.vfoa_band

            self.__freq_last = __vfoa
        else:
            self.p_status("FREQ ") # print out our state

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
    #  Goes bad
    #      0x01 24         01     C0      02      garbage
    #   0 is LSB
    #   2 is cw
    #   6 is AM
    def mode(self): # not likely the real mode change as only some issue this message
        #  must be some other primary event
        #hexdump(self.payload_copy)
        #print("Length",self.payload_len)

        if self.check_msg_valid():
            return

        self.split_status = self.payload_copy[0x00b3] # message #0xd400 @ 0x0001
        self.modeA  = self.payload_copy[0x00bc]
        self.filter = self.payload_copy[0x00bd]+1
        self.datamode = self.payload_copy[0x00be]
        self.frequency()


    # PTT sequence
    # 0xe8-00 - see Github Wiki pages for examples of mesaage ID flow
    # 0xe8-01 is spectrum data
    def ptt(self):
        #hexdump(self.payload_copy)
        #print("Length",self.payload_len)

        if self.check_msg_valid():
            return

        # watch for PTT value changes
        if (self.vfoa_band != ""):   # block PTT until we know what band we are on
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

                        # skip the band switch and delay if on the same band
                        if (self.vfoa_band != self.__vfoa_band_split_Tx):

                            self.p_status("SPLtx")
                            self.band_io_output(self.vfoa_band)
                            time.sleep(self.PTT_hang_time)
                            print("Delay:",self.PTT_hang_time,"sec")
                        else:
                            self.p_status(" DUP ")

                        self.ptt_io_output(self.vfoa_band, self.ptt_state)
                    else:
                        self.p_status(" PTT ")
                        self.ptt_io_output(self.vfoa_band, self.ptt_state)

                if (self.ptt_state == 0):
                    #print("VFO A Band = ", self.vfoa_band, " ptt_state is RX ", self.ptt_state, " Msg ID ", hex(self.payload_copy[0x0001]))
                    if (self.split_status == 1): # swap selected and unselected when split is on during TX
                        self.vfoa_band = self.__vfoa_band_split_Tx
                        self.selected_vfo = self.__selected_vfo_split_Tx

                        # skip the band switch and delay if on the same band
                        if (self.vfoa_band != self.vfob_band):
                            self.p_status("SplRx")
                            self.ptt_io_output(self.vfoa_band, self.ptt_state)
                            time.sleep(self.PTT_hang_time)
                            print("Delay:",self.PTT_hang_time,"sec")
                            self.band_io_output(self.vfoa_band)
                        else:
                            #self.p_status(" DUP ")
                            self.ptt_io_output(self.vfoa_band, self.ptt_state)
                            pass
                    else:
                        #self.p_status(" PTT ")
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
        print("(case_default) Unknown message,ID:0x"+format(self.payload_ID,'04x')+"  Length:", __payload_len)
        return "no match found"

    def colored(self, r, g, b, text):
        return f"\033[38;2;{r};{g};{b}m{text}\033[0m"

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

    # This is a list of observed message IDs.
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
            case 0x0000: self.unhandled(),  # 0x00 00 - 260 bytes  2nd message at startup
            case 0x0001: self.unhandled(),  # 0x00 01 - 264 bytes in DV mode next to 04 packets spectrum likely
            case 0x0002: self.unhandled(),  # 0x00 02 - 520 bytes on 2M SSB
            case 0x0401: self.unhandled(),  # 0x04 01 - 268 byte in DV mode, was all zeros
            case 0x0403: self.unhandled(),  # 0x04 03 - 780 byte in DV mode, was all zeros
            case 0x0801: self.mode(),       # 0x08 01 - 272 byte payload, show up on mode change around DV mode has freq, mode, filt all 
            case 0x0802: self.dump(),       # 0x08 02 - 528 byte was on 2M CW
            case 0x0803: self.unhandled(),  # 0x08 03 - 784 byte spectrum       on 2M and other bands SSB
            #case 0x0b: self.dump(),        # 0x0b xx - ??
            case 0x0c00: self.dump(),#self.mode(),  # 0x0c 00 - ?? byte unknown data, not freq, lots of them saw at satartup while in DV/FM mode
            case 0x0c01: self.unhandled(),  # 0x0c 01 - 276 byte on 23cm FM all 0s
            case 0x1001: self.unhandled(),  # 0x10 01 - 280 byte was on 2M CW
            case 0x1003: self.unhandled(),  # 0x10 03 - 792 byte spectrum maybe
            case 0x1401: self.unhandled(),  # 0x14 01 - 284 byte spectrum maybe
            case 0x1403: self.unhandled(),  # 0x14 03 - 796 byte unknown data, not freq, lots of them
            case 0x1800: self.unhandled(),  # 0x18 00 - 32 bytes continuous  unknown data
            # this usually has good data but on 23cm FM at least once it was all zeros
            case 0x1801: self.case_x18(),self.frequency(),   # 0x18-01 - 288 bytes for band chg, preamp, atten, likely more
            #  1801 on 5G afer PTT got a string of these but the data was half 0s and half NEA type data, not the usual radio settings data -  Is this G onlybehavior?
            case 0x1802: self.dump(),       # 0x18 02 - 544 bytes on 2M SSB
            case 0x1803: self.unhandled(),  # 0x18 03 - 800 bytes lots of 0s adn some GPS near end.  Surrounded by 30, 40, a d0, then 54 an 64 IDs. Was in DV/FM
            case 0x1c00: self.unhandled(),  # 0x1c 00 - 0x23 bytes NMEA has oocasional $GPGGA, slows or stops when squelch is open on good signal
            case 0x1c01: self.unhandled(),  # 0x1c 01 - 292 bytes was on 23cm FM
            case 0x1c03: self.unhandled(),  # 0x1c 03 - 804 bytes was on 2M CW
            case 0x2001: self.unhandled(),  # 0x20 01 - 296 bytes was on 23cm FM all 0s
            case 0x2002: self.unhandled(),  # 0x20 02 - 552 bytes was on 2N CW
            case 0x2003: self.unhandled(),  # 0x20 03 - 808 bytes was on 2N CW
            case 0x2400: self.unhandled(),  # 0x24 00 - 88 bytes NMEA data, slow intermittent
            case 0x2401: self.mode(),       # 0x24 01 - 300 bytes  get on filter change.  Has freq, mode, filt etc
            case 0x2403: self.dump(),       # 0x24 03 - 812 bytes on 2M SSB
            case 0x2801: self.mode(),       # 0x28 01 - 304 bytes  get on filter change in SSB mode, mode changes to RTTY,  has freq, mode and all.
            case 0x2802: self.dump(),       # 0x28 02 - 560 bytes  on 2M SSB
            case 0x2803: self.unhandled(),  # 0x28 03 - 816 bytes  was n 5G FM doing PTT 
            case 0x2c00: self.unhandled()   # 0x2c 00 - 52 bytes follows PTT.  unknown data  NMEA during RX. 
            # this usually has good data but on 2M and 23cm FM at least once it was all zeros
            case 0x2c01: self.mode(),self.frequency(), # 0x2c 01 - 308 bytes get on mode change, has frequency data in it both vfos
            case 0x2c03: self.unhandled()   # 0x2c 03 - ?? bytes was in 2M FM got invalid Mode Filt, DataM values
            case 0x3001: self.unhandled(),  # 0x30 01 - 312 bytes NMEA data
            case 0x3002: self.unhandled(),  # 0x30 02 - 568 bytes was on 2M CW
            case 0x3003: self.unhandled(),  # 0x30 03 - NMEA data
            case 0x3400: self.unhandled(),  # 0x34 00 - 0x13 bytes $GNZDA NMEA data, usually 0s
            case 0x3401: self.unhandled(),  # 0x34 01 - 316 bytes was on 23cm FM
            case 0x3402: self.unhandled(),  # 0x34 02 - 572 bytes was on 2M CW
            case 0x3403: self.unhandled(),  # 0x34 03 - 828 bytes 70cm FM spectrum likely
            case 0x3800: self.unhandled(),  # 0x38 00 - 64 bytes NMEA data,like $GNZDA  mostly 0s, msg rate speeds up in TX
            case 0x3801: self.unhandled(),  # 0x38 01 - 320 bytes was on 23cm FM
            case 0x3802: self.unhandled(),  # 0x38 02 - 576 bytes was on 2M CW
            case 0x3c00: self.unhandled(),  # 0x3c 00 - 68 bytes NMEA, $GPGGA, $GNZDA, $GLGSV  Fast rate during TX
            case 0x3c02: self.unhandled(),  # 0x3c 02 - 580 bytes was on 2M CW
            case 0x3c03: self.unhandled(),  # 0x3c 03 - 836 bytes on 70cm FM spectrum likley
            case 0x4000: self.unhandled(),  # 0x40 00 - 72 bytes NMEA data. On PTT and on band change
            case 0x4001: self.unhandled(),  # 0x40 01 - 328 bytes was on 23cm FM
            case 0x4003: self.unhandled(),  # 0x40 03 - 840 bytes 70cm FM spectrum likely
            case 0x4400: self.unhandled(),  # 0x44 00 - 0x4b bytes NMEA data shows on startup of radio
            case 0x4401: self.unhandled(),  # 0x44 01 - 332 bytes was on 23cm FM
            case 0x4402: self.unhandled(),  # 0x44 02 - 332 bytes was on 2M CW
            case 0x4403: self.unhandled(),  # 0x44 03 - 844 bytes Looks like spectrum data, was in RTTY switched to AM and 23cm to RTTY could be initial screen draw as happens on band change
            case 0x4801: self.unhandled(),  # 0x48 01 - 336 bytes  FM and DV mode on 2.3G  all 0s
            case 0x4802: self.unhandled(),  # 0x48 02 - 584 bytes  on 2M CW
            case 0x4803: self.unhandled(),  # 0x48 03 - 848 bytes  Unknkown, was in FM and DV\FM, issued on switch from DV to SSB and back to DV
            case 0x4c01: self.unhandled(),  # 0x4c 01 - 356 bytes was in DV/FM all 0s   Spectrum in AM mode  Can visualize teh APRS bursts in the middle of the data range.
                                            #  when spectrum ref is lowered, data becomes 0s and then stops.  Only strong sugs burst packets
            case 0x4c02: self.unhandled(),  # 0x4c 02 - 596 bytes  USB 2.4G  all zero quiet band
            case 0x4c03: self.unhandled(),  # 0x4c 03 - 852 bytes  DV\FM, likely spectrum
            case 0x5000: self.unhandled(),  # 0x50 00 - 88 bytes NMEA data
            case 0x5001: self.unhandled(),  # 0x50 01 - 344 bytes Showed up in DD mode on 2G, also on 2M SSb a0s
            case 0x5003: self.unhandled(),  # 0x50 03 - 856 bytes 1 time on TX start, lots of 0 ending with NMEA data
            case 0x5401: self.unhandled(),  # 0x54 01 - 348 bytes NMEA data in DV/FM mode
            case 0x5402: self.unhandled(),  # 0x54 02 - 604 bytes spectrum likely 70cm FM
            case 0x5801: self.unhandled()   # 0x58 01 - 352 bytes was in FM on 5GHz and 2M jsut spectrum or similar
            case 0x5802: self.unhandled(),  # 0x58 02 - 608 bytes was in FM and SSB spectrum likely
            case 0x5c01: self.unhandled(),  # 0x5c 01 - 356 bytes was in DV/FM all 0s
            case 0x5c02: self.unhandled(),  # 0x5c 02 - 612 bytes in AM mode, looks like spectrum  also  on 70cm FM
            case 0x6000: self.unhandled(),  # 0x60 00 - 104 bytes NMEA data
            case 0x6001: self.unhandled(),  # 0x60 01 - 360 bytes was on 23cm FM
            case 0x6002: self.unhandled(),  # 0x60 02 - 616 bytes spectrum likely on 70cm FM
            case 0x6400: self.unhandled(),  # 0x64 00 - 108 bytes NMEA data
            case 0x6401: self.unhandled(),  # 0x64 01 - 364 bytes NMEA data - burst of packets
            case 0x6402: self.unhandled(),  # 0x64 02 - 620 bytes NMEA data - burst of packets
            case 0x6800: self.unhandled(),  # 0x68 00 - 112 bytes NMEA data.Zeros in DV/FM
            case 0x6801: self.unhandled(),  # 0x68 01 - 220 bytes was on 23cm FM
            case 0x6802: self.unhandled(),  # 0x68 02 - 624 bytes ?? 
            case 0x6c00: self.unhandled(),  # 0x6c 00 - 116 bytes NMEA data
            case 0x6c01: self.unhandled(),  # 0x6c 01 - 372 bytes was on 23cm FM
            case 0x7000: self.unhandled(),  # 0x70 00 - 120 bytes NMEA on RX, 0s on TX
            case 0x7001: self.unhandled(),  # 0x70 01 - 376 bytes Was on 23cm FM
            case 0x7400: self.dump(),       # 0x74 00 - 124 bytes ??
            case 0x7401: self.unhandled(),  # 0x74 01 - 380 bytes All 0s
            case 0x7402: self.unhandled(),  # 0x74 02 - 636 bytes On 2M CW
            case 0x7800: self.unhandled(),  # 0x78 00 - 128 bytes NMEA data 
            case 0x7801: self.unhandled(),  # 0x78 01 - 120 bytes NMEA on RX, 0s on TX
            case 0x7c00: self.unhandled(),  # 0x7c 00 - 132 bytes NMEA data
            case 0x7c01: self.unhandled(),  # 0x7c 01 - 388 bytes was on 23cm FM
            case 0x8000: self.unhandled(),  # 0x80 00 - NMEA data
            case 0x8001: self.unhandled(),  # 0x80 01 - 392 bytes was on 23cm FM
            case 0x8002: self.unhandled(),  # 0x80 02 - 648 bytes was on 70cm changing modes
            #case 0x84: self.dump(),       # 0x84 xx - ?? bytes ??
            case 0x8800: self.unhandled(),  # 0x88 00 - 144 bytes mostly 0s
            case 0x8801: self.unhandled(),  # 0x88 01 - 400 bytes was on 23cm FM
            case 0x8c01: self.unhandled(),  # 0x8c 01 - 404 bytes was on 23cm FM all 0s
            case 0x8c02: self.dump(),       # 0x8c 02 - 660 bytes spectrum maybe
            case 0x9001: self.unhandled(),  # 0x90 01 - 408 bytes spectrum on 2.4G
            case 0x9401: self.unhandled(),  # 0x94 01 - 412 bytes Looks like spectrum on 2.4G SSB
            case 0x9402: self.unhandled(),  # 0x94 02 - 668 bytes Looks like spectrum
            case 0x9801: self.unhandled(),  # 0x98 01 - 416 bytes on 23cm FM mostly 0s
            case 0x9802: self.unhandled(),  # 0x98 02 - 672 bytes spectrum while in 2M FM quiet band
            case 0x9c00: self.unhandled(),  # 0x9c 00 - 164 bytes saw in DV/FM. nearly all zeros,  rare message.  
            case 0x9c01: self.unhandled(),  # 0x9c 01 - 420 bytes was on 23cm FM 
            case 0xa000: self.unhandled(),  # 0xa0 00 - 168 bytes was on 23cm FM
            case 0xa002: self.unhandled(),  # 0xa0 02 - 680 bytes Spectrum likely in AM 
            case 0xa400: self.unhandled(),  # 0xa4 00 - 172 bytes shows in DV/FM mode. Looks like GPS data.  Codl just be gps mixed in
            case 0xa401: self.unhandled(),  # 0xa4 01 - 428 bytes shows in DV/FM mode. All 0s 
            case 0xa406: self.unhandled(),  # 0xa4 06 - 1448 bytes go in 2M at radio startup - first message maybe has startup stuff we need
            case 0xa800: self.unhandled(),  # 0xa8 00 - 176 bytes 2.4G all zeros no signal
            case 0xa801: self.unhandled(),  # 0xa8 01 - 488 and 432 bytes shows in DV/FM when ref level raised and APRS signal and on 2.4G
            case 0xa802: self.unhandled(),  # 0xa8 02 - 688 and 432 bytes shows in DV/FM when ref level r
            case 0xa803: self.frequency(),  # 0xa8 03 - 944 bytes shows in FM afer a radio restart  3rd startup message
            case 0xac00: self.unhandled(),  # 0xac 00 - 180 bytes All 0s
            case 0xac01: self.unhandled(),  # 0xac 01 - 436 bytes on 2M USB
            case 0xac02: self.dump(),       # 0xac 02 - 692 bytes 2M FM spectrum likely
            case 0xb000: self.unhandled(),  # 0xbo 00 - 184 bytes was on 23cm FM
            case 0xb001: self.unhandled(),  # 0xbo 01 - 440 bytes was on 23cm FM
            case 0xb002: self.unhandled(),  # 0xbo 02 - 696 bytes on 5G FM/ or DV 
            case 0xb003: self.unhandled(),  # 0xbo 03 - 952 bytes shows on radio startup, mostly zero filled
            case 0xb400: self.unhandled(),  # 0xb4 00 - 188 bytes  was on 2M CW all 0s
            case 0xb401: self.unhandled(),  # 0xb4 01 - 444 bytes was pon 23cm Al l0s
            case 0xb402: self.unhandled(),  # 0xb4 02 - 700 bytes  spectrum maybe on 2M FM after startup
            case 0xb403: self.unhandled(),  # 0xb4 03 - 956 bytes  spectrum maybe on 2M FM after startup - 5th startup msg
            case 0xb800: self.unhandled(),  # 0xb8 00 - 192 bytes  On 2M SSB
            case 0xb801: self.unhandled(),  # 0xb8 01 - 448 bytes  2.4G band SSB all zeros quiet band, same for 23cm FM
            case 0xb802: self.unhandled(),  # 0xb8 02 - 704 bytes  spectrum likely
            case 0xbc00: self.unhandled(),  # 0xbc 00 - 196 bytes  was on 2M CW
            case 0xbc01: self.unhandled(),  # 0xbc 01 - 452 bytes  was on 23cm FM all zeros
            case 0xc000: self.unhandled(),  # 0xc0 00 - 200 bytes  was on 23cm FM
            case 0xc001: self.unhandled(),  # 0xc0 01 - 488 bytes  was in DV/FM msotly 0s nmea data
            case 0xc002: self.unhandled(),  # 0xc0 02 - xx bytes  was in DV/FM msotly 0s nmea data
            case 0xc003: self.unhandled(),  # 0xc0 02 - 788 bytes  was on 2M CW
            case 0xc400: self.unhandled(),  # 0xc4 00 - 204 bytes  RTTY spectrum/GPS maybe
            case 0xc401: self.unhandled(),  # 0xc4 01 - 460 bytes  On 2M SB
            case 0xc402: self.unhandled(),  # 0xc4 02 - 716 bytes  was in DV/FM mostl;y 0s, some nmea
            case 0xc800: self.unhandled(),  # 0xc8 00 - 208 bytes  RTTY on 23cm spectrum maybe
            case 0xc801: self.unhandled(),  # 0xc8 01 - 464 bytes  was in DV/FM mosty all zeros, maybe spectrum
            case 0xcc00: self.unhandled(),  # 0xcc 00 - 212 bytes  was on 23cm FM all 0s mostly
            case 0xcc01: self.unhandled(),  # 0xcc 01 - 468 bytes  was on 23cm FM all 0s mostly
            case 0xcc02: self.unhandled(),  # 0xcc 02 - 724 bytes  2M FM  spectrum
            case 0xd000: self.unhandled(),  # 0xd0 00 - 216 bytes ???PTT start event???, freq at 0xb8 for current VFO.  Works on simplex, duplex, no split, no VFOb data
            case 0xd001: self.unhandled(),  # 0xd0 01 - 472 bytes 5G DD mode   all 0s
            case 0xd400: self.case_xD4(),   # 0xd4 00 - 220 bytes get Split msg on d4-00 has frequency but this is short msg
            case 0xd401: self.unhandled(),  # 0xd4 01 - 476 bytes Mostly zeros, came after a PTT event
            case 0xd402: self.unhandled(),  # 0xd4 02 - 732 bytes Mostly zeros on 70cm switching FM to SSB folowing d400 mode change
            case 0xd800: self.frequency(),  # 0xd8 00 - 224 bytes data for freq, mode and more
            case 0xd801: self.unhandled(),  # 0xd8 01 - 480 bytes All zeros on 23cm FM
            case 0xdc00: self.unhandled(),  # 0xdc 00 - 228 bytes rarely shows, has NMEA data in it showed when ref level raised on 2.4G
            case 0xdc01: self.unhandled(),  # 0xdc 01 - 484 bytes was on 2M FM
            case 0xe000: self.unhandled(),  # 0xe0 00 - 232 bytes was on 23cm FM
            case 0xe001: self.unhandled(),  # 0xe0 01 - 488 bytes in FM spectrum on band change to 23cm
            case 0xe002: self.unhandled(),  # 0xe0 02 - 744 bytes in DV/FM spectgrum+GPS data - 4th startup message
            case 0xe400: self.unhandled(),  # 0xe4 00 - 236 bytes was on 23cm FM
            case 0xe401: self.unhandled(),  # 0xe4 01 - 492 bytes shows when activity on spectrum was in DV
            case 0xe402: self.unhandled(),  # 0xe4 02 - 748 bytes was on 2M CW
            case 0xe800: self.ptt(),        # 0xe8 00 - ?? bytes tx/rx changover trigger, e801 normal RX or TX state.  PTT is last byte but may be in others also. Byte 0xef is PTT state
            case 0xe801: self.unhandled(),  # 0xe8 01   ?? bytes is spectrum data on RX when enabled 0
            case 0xe802: self.unhandled(),  # 0xe8 02   752 bytes was on 2.4G FM
            case 0xec00: self.frequency(),  # 0xec 00 - 244 bytes occurs on data-mode (digital mode) change
            case 0xec02: self.unhandled(),  # 0xec 02 - 0x133 bytes filled with zeros and blocks of gps data
            # the 04, 54, 64 f4, fc ID showed up when there was a signal in DV/FM listeing to packet.  Filled with 0s.  WIl lalso show up when a signal is off freq
            case 0xf000: self.unhandled(),  # 0xf0 00 - 248 bytes was in DV mode. Looks like spectrum.  had squelch on in FM
            case 0xf001: self.unhandled(),  # 0xf0 01 - 504 bytes was in DV mode. Looks like spectrum.  had squelch on in FM
            case 0xf002: self.unhandled(),  # 0xf0 02 - ??bytes was in DV mode.
            case 0xf400: self.unhandled(),  # 0xf4 00 - 252 bytes NMEA data shows up when a large signal was on teh spectgrum and the ref line was < 0 which squelces f4 02 in DV mode.
            case 0xf402: self.unhandled(),  # 0xf4 02 - 764 bytes NMEA data at end, looks like spectrum in DV mode.  Stops when ref line <0
            case 0xf800: self.unhandled(),  # 0xf8 00 - 255 bytes shows up periodically in middle of TX streams and other times
            case 0xf801: self.unhandled(),  # 0xf8 01 - 512 bytes was on 2M CW
            case 0xfc00: self.unhandled(),  # 0xfc 00 - 260 bytes Looks like spectrum/NMEA data.  Saw in many palces, during TX, in FM to SSB transition, DV/FM            
            case _: self.case_default()     # anything we have not seen yet comes to here


    def switch_case(self, payload, payload_len):
        self.payload_copy = payload
        self.payload_ID_byte = payload[0x0001]
        self.payload_Attrib_byte = payload[0x0002]
        self.payload_len = payload_len
        self.payload_ID = (self.payload_ID_byte << 8)+self.payload_Attrib_byte

        # Turn off all lines below this to see only hex data on screen
        #if (self.payload_ID == 0xa4):   # a0 a4 a8 ac
         #   hexdump(payload)
         #   print(self.payload_len, "\n")

        # Turn this print ON to see all message IDs passing through here
        #print("Switch on 0x"+format(self.payload_ID,"04x")+"  Len:", format(self.payload_len))

        #Turn this on to only see hex dumps for any and all packets
        #self.dump()

        # most large payloads are spectrum data and we can ignore those.
        if (self.payload_len < 360 or self.payload_ID == 0xa803):
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
        GPIO.cleanup()


if __name__ == '__main__':
    import sys
    io = OutputHandler()  # instantiate our classes
    bd = BandDecoder()
    mh = Message_handler()
    io.gpio_config()
    sys.exit(tcp_sniffer(sys.argv))
