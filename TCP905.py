#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  TCP905.py
#
#  v3  Feb 14, 2025 K7MDL
#  IC-905 Ethernet Band Decoder
#
#  Uses tcpdump in a subprocess to filter and process sniffed packets
#  between the IC-905 Control Head and the RF Unit to extract frequency
#  and PTT events to operate a band decoder which in turn can operate
#  things like antenna switches and/or key an amplifer.
#  12 GPIO pins are configured in the code below.
#  See the project wiki pages for details
#
#  Connect a managed switch with the control head and RF unit in a VLAN
#  Enable port mirroring to a 3rd switch port.
#  Plug in a Raspberry Pi 3B or 4B to the mirror port.
#
# ------------------------------------------------------------------------
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
#from scapy.all import *
import os
import sys
import numpy as np
import time
import RPi.GPIO as GPIO
import subprocess as sub
from threading import Timer
from typing import Callable
from datetime import datetime as dtime

#  if dht is enabled, and connection is lost, ther program will try to recover the connection during idle periods
dht11_enable = True  # enables the sensor and display of temp and humidity
dht11_OK = True   #  Tracks online status if connection to the DHT11 temp sensor
dht11_poll_time = 300   # pol lthe DHT11 (if installed) every X seconds.
TempC = 0
TempF = 0
Humidity = 0

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
                      'band_pin':5,  #4,
                   'band_invert':False,
                       'ptt_pin':0,  #16, for 4 relay hat,  #17, for 3 relay hat, 0 for antenna only and no PTT
                    'ptt_invert':False,
                 },
                 0x02 : {
                      'band_pin':6,  #3,
                   'band_invert':False,
                       'ptt_pin':0,
                    'ptt_invert':True,
                 },
                 0x04 : {
                      'band_pin':13, #2,
                   'band_invert':False,
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


#  __________________________________________________________________
#
#  GPIO outputs for Band and PTT
#  __________________________________________________________________
#

class OutputHandler:

    def get_time(self):
        d = dtime.now()
        return d.strftime("%m/%d/%y %H:%M:%S")


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
                print(p,"Output for "+b+" Pattern:"+bp, flush=True)

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
                print(t,"Output for "+b+" Pattern:"+p, flush=True)
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

#-----------------------------------------------------------------------------
#
#   Threaded timer for periodic logging of things such as temp, or
#     restart a failed temp device connection without blocking the main program
#
#-----------------------------------------------------------------------------

class RepeatedTimer(object):
    def __init__(self, interval: int, function: Callable, args=None, kwargs=None):
        super(RepeatedTimer, self).__init__()
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = [] if args is None else args
        self.kwargs = {} if kwargs is None else kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

#  __________________________________________________________________
#
#  Packet data processing function thread object
#  __________________________________________________________________
#

class DecoderThread(object):
    def __init__(self, function: Callable, args=None, kwargs=None):
        super(DecoderThread, self).__init__()
        self._timer = None
        self.function = function
        self.args = [] if args is None else args
        self.kwargs = {} if kwargs is None else kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

#  __________________________________________________________________
#
#  Packet data processing functions
#  __________________________________________________________________
#

class BandDecoder(): #OutputHandler):
# We are inheriting from OutputHandler class so we can access its functions
#   and variables as if they were our own.
    vfoa_band = ""
    vfoa_band_split_Tx = ""
    vfob_band = ""
    selected_vfo = 0
    unselected_vfo = 255
    selected_vfo_split_Tx = 0
    split_status = 255
    preamp_status = 255
    atten_status =255
    ptt_state = 0
    modeA = 255
    filter = 255
    datamode = 255
    in_menu = 0
    payload_len = 0
    payload_copy = ""
    payload_ID = 0
    payload_ID_byte = 0
    payload_Attrib_byte = 0
    frequency_init = 0
    
    def __init__(self):
        self.__offset = 0
        self.__freq_last = 0
        self.__vfoa_band_last = 255
        self.__ptt_state_last = 255
        self.PTT_hang_time = 0.3
        self.__split_status_last = 255

    #--------------------------------------------------------------------
    #  Process config file
    #--------------------------------------------------------------------
                
    def str_to_bool(self, s):
        return {'true': True, 'false': False}.get(s.lower(), False)


    def read_DHT(self, key_value_pairs):
        #for key in key_value_pairs:
        dht11_enable = self.str_to_bool(key_value_pairs['DHT11_ENABLE'])
        dht11_poll_time = int(key_value_pairs['DHT11_TIME'])


    def read_split(self, key_value_pairs):        
        #Initialize split based on last known status
        self.split_status = int(key_value_pairs['RADIO_SPLIT'])
        #print("Read file",self.split_status)
        
        
    def read_band(self, key_value_pairs): 
        # Initialize the band and VFOs to the last saved values, lost likely will be correct.  
        # Alternative is to do nothng and block PTT
        __band_name = key_value_pairs['RADIO_BAND']
        __offset = Freq_table[__band_name]['offset']
        self.vfoa_band = self.vfob_band = self.vfoa_band_split_Tx = __band_name
        self.selected_vfo = self.unselected_vfo = self.selected_vfo_split_Tx = Freq_table[__band_name]['lower_edge'] + __offset +1
        self.ptt_state = 0
        
        
    def read_patterns(self, key_value_pairs):
        Freq_table['2M']['band'] = band_2M = int(key_value_pairs['BAND_2M'],base=16)
        Freq_table['2M']['ptt'] = ptt_2M = int(key_value_pairs['PTT_2M'],base=16)
        #print("2M Band pattern:  ", hex(band_2M), "PTT:", hex(ptt_2M))
        
        Freq_table['70cm']['band'] = band_70cm = int(key_value_pairs['BAND_70cm'],base=16)
        Freq_table['70cm']['ptt'] =ptt_70cm = int(key_value_pairs['PTT_70cm'],base=16)
        #print("70cm Band pattern:", hex(band_70cm), "PTT:", hex(ptt_70cm))
        
        Freq_table['23cm']['band'] = band_23cm = int(key_value_pairs['BAND_23cm'],base=16)
        Freq_table['23cm']['ptt'] =ptt_23cm = int(key_value_pairs['PTT_23cm'],base=16)
        #print("23cm Band pattern:", hex(band_23cm), "PTT:", hex(ptt_23cm))
        
        Freq_table['13cm']['band'] = band_13cm = int(key_value_pairs['BAND_13cm'],base=16)
        Freq_table['13cm']['ptt'] =ptt_13cm = int(key_value_pairs['PTT_13cm'],base=16)
        #print("13cm Band pattern:", hex(band_13cm), "PTT:", hex(ptt_13cm))
        
        Freq_table['6cm']['band'] = band_6cm = int(key_value_pairs['BAND_6cm'],base=16)
        Freq_table['6cm']['ptt'] =ptt_6cm = int(key_value_pairs['PTT_6cm'],base=16)
        #print("6cm Band pattern: ", hex(band_6cm), "PTT:", hex(ptt_6cm))
        
        Freq_table['3cm']['band'] = band_3cm = int(key_value_pairs['BAND_3cm'],base=16)
        Freq_table['3cm']['ptt'] =ptt_3cm = int(key_value_pairs['PTT_3cm'],base=16)
        #print("3cm Band pattern: ", hex(band_3cm), "PTT:", hex(ptt_3cm))


    def read_band_pins(self, key_value_pairs):    
        IO_table[0x01]['band_pin'] = gpio_band_0_pin = int(key_value_pairs['GPIO_BAND_0_PIN'])
        IO_table[0x01]['band_invert'] = gpio_band_0_pin_invert = self.str_to_bool(key_value_pairs['GPIO_BAND_0_PIN_INVERT'])
        #print("Band Pin 0: ", gpio_band_0_pin, " Invert:", gpio_band_0_pin_invert)

        IO_table[0x02]['band_pin'] = gpio_band_1_pin = int(key_value_pairs['GPIO_BAND_1_PIN'])
        IO_table[0x02]['band_invert'] = gpio_band_1_pin_invert = self.str_to_bool(key_value_pairs['GPIO_BAND_1_PIN_INVERT'])
        #print("Band Pin 1: ", gpio_band_1_pin, " Invert:", gpio_band_1_pin_invert)
        
        IO_table[0x04]['band_pin'] = gpio_band_2_pin = int(key_value_pairs['GPIO_BAND_2_PIN'])
        IO_table[0x04]['band_invert'] = gpio_band_2_pin_invert = self.str_to_bool(key_value_pairs['GPIO_BAND_2_PIN_INVERT'])
        #print("Band Pin 2: ", gpio_band_2_pin, " Invert:", gpio_band_2_pin_invert)
        
        IO_table[0x08]['band_pin'] = gpio_band_3_pin = int(key_value_pairs['GPIO_BAND_3_PIN'])
        IO_table[0x08]['band_invert'] = gpio_band_3_pin_invert = self.str_to_bool(key_value_pairs['GPIO_BAND_3_PIN_INVERT'])
        #print("Band Pin 3: ", gpio_band_3_pin, " Invert:", gpio_band_3_pin_invert)
        
        IO_table[0x10]['band_pin'] = gpio_band_4_pin = int(key_value_pairs['GPIO_BAND_4_PIN'])
        IO_table[0x10]['band_invert'] = gpio_band_4_pin_invert = self.str_to_bool(key_value_pairs['GPIO_BAND_4_PIN_INVERT'])
        #print("Band Pin 4: ", gpio_band_4_pin, " Invert:", gpio_band_4_pin_invert)
        
        IO_table[0x20]['band_pin'] = gpio_band_5_pin = int(key_value_pairs['GPIO_BAND_5_PIN'])
        IO_table[0x20]['band_invert'] = gpio_band_5_pin_invert = self.str_to_bool(key_value_pairs['GPIO_BAND_5_PIN_INVERT'])
        #print("Band Pin 5: ", gpio_band_5_pin, " Invert:", gpio_band_5_pin_invert)
        
        
    def read_ptt_pins(self, key_value_pairs):    
        IO_table[0x01]['ptt_pin'] = gpio_ptt_0_pin = int(key_value_pairs['GPIO_PTT_0_PIN'])
        IO_table[0x01]['ptt_invert'] = gpio_ptt_0_pin_invert = self.str_to_bool(key_value_pairs['GPIO_PTT_0_PIN_INVERT'])
        #print("PTT Pin 0: ", gpio_ptt_0_pin, " Invert:", gpio_ptt_0_pin_invert)
        
        IO_table[0x02]['ptt_pin'] = gpio_ptt_1_pin = int(key_value_pairs['GPIO_PTT_1_PIN'])
        IO_table[0x02]['ptt_invert'] = gpio_ptt_1_pin_invert = self.str_to_bool(key_value_pairs['GPIO_PTT_1_PIN_INVERT'])
        #print("PTT Pin 1: ", gpio_ptt_1_pin, " Invert:", gpio_ptt_1_pin_invert)
        
        IO_table[0x04]['ptt_pin'] = gpio_ptt_2_pin = int(key_value_pairs['GPIO_PTT_2_PIN'])
        IO_table[0x04]['ptt_invert'] = gpio_ptt_2_pin_invert = self.str_to_bool(key_value_pairs['GPIO_PTT_2_PIN_INVERT'])
        #print("PTT Pin 2: ", gpio_ptt_2_pin, " Invert:", gpio_ptt_2_pin_invert)
        
        IO_table[0x08]['ptt_pin'] = gpio_ptt_3_pin = int(key_value_pairs['GPIO_PTT_3_PIN'])
        IO_table[0x08]['ptt_invert'] = gpio_ptt_3_pin_invert = self.str_to_bool(key_value_pairs['GPIO_PTT_3_PIN_INVERT'])
        #print("PTT Pin 3: ", gpio_ptt_3_pin, " Invert:", gpio_ptt_3_pin_invert)
        
        IO_table[0x10]['ptt_pin'] = gpio_ptt_4_pin = int(key_value_pairs['GPIO_PTT_4_PIN'])
        IO_table[0x10]['ptt_invert'] = gpio_ptt_4_pin_invert = self.str_to_bool(key_value_pairs['GPIO_PTT_4_PIN_INVERT'])
        #print("PTT Pin 4: ", gpio_ptt_4_pin, " Invert:", gpio_ptt_4_pin_invert)
        
        IO_table[0x020]['ptt_pin'] = gpio_ptt_5_pin = int(key_value_pairs['GPIO_PTT_5_PIN'])
        IO_table[0x20]['ptt_invert'] = gpio_ptt_5_pin_invert = self.str_to_bool(key_value_pairs['GPIO_PTT_5_PIN_INVERT'])
        #print("PTT Pin 5: ", gpio_ptt_5_pin, " Invert:", gpio_ptt_5_pin_invert)

    def init_band(self, key_value_pairs):        
        self.read_DHT(key_value_pairs)
        self.read_patterns(key_value_pairs)
        self.read_band_pins(key_value_pairs)
        self.read_ptt_pins(key_value_pairs)
        self.vfoa_band = self.frequency()
        self.ptt()

    def write_split(self, split):
        file_path = os.path.expanduser('~/.Decoder905.split')
        try:
            with open(file_path,'w+') as file:
                split_str = "RADIO_SPLIT="+str(split)
                file.write(split_str)
        except FileNotFoundError:
            print(f"The file {file} does not exist in the home directory.")
        except Exception as e:
            print(f"An error occured: {e}")


    def write_band(self, band):
        file_path = os.path.expanduser('~/.Decoder905.band')
        try:
            with open(file_path,'w+') as file:
                band_str = "RADIO_BAND="+band
                file.write(band_str)
        except FileNotFoundError:
            print(f"The file {file} does not exist in the home directory.")
        except Exception as e:
            print(f"An error occured: {e}")


    def hexdump(self, data: bytes):
        def to_printable_ascii(byte):
            return chr(byte) if 32 <= byte <= 126 else "."

        offset = 0
        while offset < len(data):
            chunk = data[offset : offset + 16]
            hex_values = " ".join(f"{byte:02x}" for byte in chunk)
            ascii_values = "".join(to_printable_ascii(byte) for byte in chunk)
            print(f"{offset:08x}  {hex_values:<48}  |{ascii_values}|", flush=True)
            offset += 16

    # -------------------------------------------------------------------
    #
    # DHT-11 Humidity and Temperature sensor
    #
    #   The DHT-11 and CPU temperature is logged with each print to
    #       screen at the end of the print line.
    #
    #--------------------------------------------------------------------

    def get_cpu_temp(self):
        temp = os.popen("vcgencmd measure_temp").readline()
        return temp.replace("temp=", "").strip()[:-2]

    def write_temps(self, line):   #, file):
        file_path = os.path.expanduser('~/Temperatures.log')
        try:
            with open(file_path,'a') as file:
                file.write(line)
        except  FileNotFoundError:
            print(f"The file {file} does not exist in the home directory.")
        except Exception as e:
            print(f"An error occured: {e}")

    def read_dht(self, file):
        f = open(file,"rt")
        value = int(f.readline())
        f.close
        return value

    def read_temps(self):
        global dht11_OK
        global dht_enable
        global TempC
        global TempF
        global Humidity

        t = h = tF = 2    #  a value of zero inidicates failure so starting with 1

        if (dht11_enable == False):   # failures result in bus timeout delays so do not try again
            return t, h, tF

        try:
            if  (dht11_OK):
                t = self.read_dht("/sys/bus/iio/devices/iio:device0/in_temp_input")/1000
                h = self.read_dht("/sys/bus/iio/devices/iio:device0/in_humidityrelative_input")/1000
                tF = t * (9 / 5) + 32

        # If failure is due to device not present, bus timeout delays
        # since we are running in our own thread we can retry the read and
        # bus timeouts won't affect the main radio message handling

        except RuntimeError as error:
            # Errors happen fairly often, DHT's are hard to read, just keep going
            print("DHT11 RunTime Eror =", error.args[0], flush=True)
            t = h = tF = 0
            dht11_OK = True

        except Exception as error:
            print("DHT11 Read error = ",error, flush=True)
            t = h = tF = 0
            dht11_OK = True
            #raise error

        TempC = t
        TempF = tF
        Humidity = h

        return t, h, tF


    def temps(self):
        if dht11_enable:
            (temp, hum, temp_F) = self.read_temps()
        else:
            temp = hum= temp_F = 0
        cpu = self.get_cpu_temp()
        tim = dtime.now()
        temp_str = (tim.strftime("%m/%d/%Y %H:%M:%S%Z")+"  Temperature: %(f)0.1f°F  %(t)0.1f°C  Humidity: %(h)0.1f%%  CPU: %(c)s°C" % {"t": temp, "h": hum, "f": temp_F, 'c': cpu})
        print(self.colored(100,120,255,"(TEMP )"), temp_str, flush=True)
        self.write_temps(temp_str+"\n")


    def check_msg_valid(self):
        if (self.payload_ID != 0xa803 and self.payload_ID != 0x0000):
            if (self.payload_copy[0x000a] != 0x44 and self.payload_copy[0x000b] != 0x00):
                #print("Rejected message from ID", format(self.payload_ID, "04x"))
                return  1 # get avoid garbage versions
            else:
                #print("Accepted message from ID", format(self.payload_ID, "04x"))
                return 0   # return 1 for bad, 0 for good


    def p_status(self, TAG):
        global TempC
        global TempF
        global Humidity
        cpu = self.get_cpu_temp()
        #tim = dtime.now()
        print(self.colored(175,210,240,"("+TAG+")"),
            #tim.strftime("%m/%d/%y %H:%M:%S%Z"),
            " VFOA Band:"+self.colored(255,225,165,format(self.vfoa_band,"4")),
            " A:"+self.colored(255,255,255,format(self.selected_vfo, "11")),
            " B:"+self.colored(215,215,215,format(self.unselected_vfo, "11")),
            " Split:"+self.colored(225,255,90,format(self.split_status, "1")),
            " M:"+format(self.modeA, "1"),
            " F:"+format(self.filter, "1"),
            " D:"+format(self.datamode, "1"),
            " P:"+format(self.preamp_status, "1"),
            " A:"+format(self.atten_status, "1"),
            " PTT:"+self.colored(115,195,110,format(self.ptt_state, "1")),
            #" Menu:"+format(self.in_menu, "1"),   #  this toggles 0/1 when in menus, and/or when there is spectrum flowing not sure which
            " Src:0x"+format(self.payload_ID, "04x"),
            #" T:%(t)0.1f°F  H:%(h)0.1f%%  CPU:%(c)s°C" % {"t": TempF, "h": Humidity, "c": cpu}, # sub in 'temp' for deg C
            flush=True)


    # If we see corrupt values then look at the source.
    # Some messages are overloaded - meaning they can have radio
    #   status or have other spectrum like data in the same length
    #   and ID+Attrib combo.  Calling check_msg_valid to filter out
    #   bad stuff based on observed first row byte patterns

    def case_x18(self):  # process items in message id # 0x18
        #self.hexdump(self.payload_copy)
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
        #self.hexdump(self.payload_copy)
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
    def get_freq(self, __payload, vfo):
        np.set_printoptions(formatter={'int':hex})
        freq_hex_dec = np.array([0, 0, 0, 0],dtype=np.uint8)

        for i in range(0, 4, 1):
            freq_hex_dec[i] = (__payload[vfo+i])
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
        #self.hexdump(self.payload_copy)
        #print("Length",self.payload_len)

        if self.check_msg_valid():
            return
        
        # Duplex used split status byte for VFO swap, just has vfoB set different with offset
        # split is updated in message ID 0xD4.  Here we can also pick it up and not wait for 
        # someone to press the split button to generate the d4 event.
        if (self.payload_ID == 0x0000):
            __vfoa = __vfob = self.selected_vfo
            self.ptt_state = 0
        elif (self.payload_ID == 0xa803):   # from startup message, different byte locations
            vfoa = 0x00fc
            vfob = 0x0108
            self.split_status  = self.payload_copy[0x005f]
            self.preamp_status = self.payload_copy[0x0160]
            self.atten_status = self.payload_copy[0x0161]
        else:
            # from another message ID that call here
            vfoa = 0x00b8
            vfob = 0x00c4
            self.split_status  = self.payload_copy[0x001b]
            # collect premp and atten via other messages.

        if (self.payload_ID != 0x0000):        
            self.modeA  = self.payload_copy[vfoa+4]
            self.filter = self.payload_copy[vfoa+5]+1
            self.datamode = self.payload_copy[vfoa+6]

            # Returns the payload hex converted to int.
            # This need to have the band offset applied next
            __vfoa = self.get_freq(self.payload_copy, vfoa)
            #print("(Freq) VFO A = ", vfoa)
            __vfob = self.get_freq(self.payload_copy, vfob)
            #print("(Freq) VFO B = ", vfob)

        if (self.vfoa_band == "13cm" or self.vfoa_band == "6cm"):
            self.atten_status = 0
            self.preamp_status = 0

        if (self.split_status != self.__split_status_last):
            self.write_split(self.split_status)
            self.__split_status_last = self.split_status

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
                io.band_io_output(self.vfoa_band)
                self.__vfoa_band_last = self.vfoa_band
                self.write_band(self.vfoa_band)  # update the status file on change

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
        #self.hexdump(self.payload_copy)
        #print("Length",self.payload_len)

        if self.check_msg_valid():
            return

        # watch for PTT value changes
        if (self.vfoa_band != ""):   # block PTT until we know what band we are on
            #print("PTT called")
            
            if self.payload_ID != 0x0000:
                if self.frequency_init == 0:
                    self.frequency()
                    self.frequency_init = 1
                self.ptt_state = self.payload_copy[0x00ef]
            else:
                self.ptt_state = 0
                #self.__ptt_state_last = 255
            
            if (self.ptt_state != self.__ptt_state_last):
                #print("PTT state =", self.ptt_state)
                if (self.ptt_state == 1):  # do not TX if the band is still unknown (such as at startup)
                    #print("PTT TX VFO A Band = ", self.vfoa_band, "VFO B Band = ", self.vfob_band, "  ptt_state is TX ", self.ptt_state, " Msg ID ", hex(self.payload_copy[0x0001]))
                    if (self.split_status == 1): # swap selected and unselected when split is on during TX
                        self.vfoa_band_split_Tx = self.vfoa_band  # back up the original VFOa band
                        self.selected_vfo_split_Tx = self.selected_vfo  # back up original VFOa
                        self.selected_vfo = self.unselected_vfo  # during TX assign b to a
                        self.vfoa_band = self.vfob_band
                        #print("PTT TX1 VFO A Band = ", self.vfoa_band, "VFO B Band = ", self.vfob_band,  " ptt_state is TX ", self.ptt_state)
                        
                        # skip the band switch and delay if on the same band
                        if (self.vfoa_band != self.vfoa_band_split_Tx):
                            self.p_status("SPLtx")
                            io.band_io_output(self.vfoa_band)
                            time.sleep(self.PTT_hang_time)
                            print("Delay:",self.PTT_hang_time,"sec")
                        else:
                            self.p_status(" DUP ")
                        io.ptt_io_output(self.vfoa_band, self.ptt_state)
                    else:
                        self.p_status(" PTT ")
                        io.ptt_io_output(self.vfoa_band, self.ptt_state)

                else:   #(self.ptt_state == 0):
                    #print("PTT-RX VFO A Band =", self.vfoa_band, "VFO B Band =", self.vfob_band, "VFOA BAND SPLIT TX =", self.vfoa_band_split_Tx, "SELECTED VFO SPLIT TX =", self.selected_vfo, " ptt_state is RX ", self.ptt_state) #, " Msg ID ", hex(self.payload_copy[0x0001]))
                    if (self.split_status == 1): # swap selected and unselected when split is on during TX
                        self.vfoa_band = self.vfoa_band_split_Tx
                        self.selected_vfo = self.selected_vfo_split_Tx
                        #print("PTT-RX1 VFO A Band = ", self.vfoa_band, "VFO B Band = ", self.vfob_band,  " ptt_state is RX ", self.ptt_state)
                        
                        # skip the band switch and delay if on the same band
                        if (self.vfoa_band != self.vfob_band):
                            self.p_status("SplRx")
                            io.ptt_io_output(self.vfoa_band, self.ptt_state)
                            time.sleep(self.PTT_hang_time)
                            print("Delay:",self.PTT_hang_time,"sec")
                            io.band_io_output(self.vfoa_band)
                        else:
                            #self.p_status(" DUP ")
                            io.ptt_io_output(self.vfoa_band, self.ptt_state)
                            pass
                    else:
                        #self.p_status(" PTT ")
                        io.ptt_io_output(self.vfoa_band, self.ptt_state)

                self.__ptt_state_last = self.ptt_state


    def TX_on(self):
        print("(Tx_on) Transmitting... - sometimes not")
        self.hexdump(self.payload_copy)
        print("(TX_on) Length:", self.payload_len)
        

    def dump(self):
        print("Dump for message 0x"+format(self.payload_ID,"04x")+"  Len:", format(self.payload_len))
        self.hexdump(self.payload_copy)
        #print("(dump) Length:", self.payload_len)


    def heartbeat(self):
        self.hexdump(self.payload_copy)
        #print("heartbeat", self.payload_copy)
        print("(heartbeat) Length:", self.payload_len)


    def unhandled(self):
        return "unhandled message"


    def case_default(self):
        self.hexdump(self.payload_copy)
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
        #print("ID:",format(ID,"04x")
        match ID:
            #case 0xYY: dump,  # example of a message routed to hex dump function for investigation
            # These are IDs I have examined and a few are (reasonably) known.
            # A lot are marked with NMEA in the payload.. IT seems way too much to be intentional
            # I would make a guess that parts of these payloads are not used and have buffer 
            #    data left over from earlier and different packets.
            case 0x0000: bd.unhandled(),  # 0x00 00 - 260 bytes  2nd message at startup
            case 0x0001: bd.unhandled(),  # 0x00 01 - 264 bytes in DV mode next to 04 packets spectrum likely
            case 0x0002: bd.unhandled(),  # 0x00 02 - 520 bytes on 2M SSB
            case 0x0401: bd.unhandled(),  # 0x04 01 - 268 byte in DV mode, was all zeros
            case 0x0403: bd.unhandled(),  # 0x04 03 - 780 byte in DV mode, was all zeros
            case 0x0800: bd.dump(),       # 0x08 00 - 440 byte was on 2M FM restarting after failure.  Could be a shutdown msg
            case 0x0801: bd.mode(),       # 0x08 01 - 272 byte payload, show up on mode change around DV mode has freq, mode, filt all 
            case 0x0802: bd.dump(),       # 0x08 02 - 528 byte was on 2M CW
            case 0x0803: bd.unhandled(),  # 0x08 03 - 784 byte spectrum       on 2M and other bands SSB
            #case 0x0b: bd.dump(),        # 0x0b xx - ??
            case 0x0c00: bd.dump(),#bd.mode(),  # 0x0c 00 - ?? byte unknown data, not freq, lots of them saw at satartup while in DV/FM mode
            case 0x0c01: bd.unhandled(),  # 0x0c 01 - 276 byte on 23cm FM all 0s
            case 0x0c02: bd.unhandled(),  # 0x0c 02 - ??? byte on 2M FM
            case 0x1001: bd.unhandled(),  # 0x10 01 - 280 byte was on 2M CW
            case 0x1003: bd.unhandled(),  # 0x10 03 - 792 byte spectrum maybe
            case 0x1401: bd.unhandled(),  # 0x14 01 - 284 byte spectrum maybe
            case 0x1403: bd.unhandled(),  # 0x14 03 - 796 byte unknown data, not freq, lots of them
            case 0x1800: bd.unhandled(),  # 0x18 00 - 32 bytes continuous  unknown data
            # this usually has good data but on 23cm FM at least once it was all zeros
            case 0x1801: bd.case_x18(),bd.frequency(),   # 0x18-01 - 288 bytes for band chg, preamp, atten, likely more
            #  1801 on 5G afer PTT got a string of these but the data was half 0s and half NEA type data, not the usual radio settings data -  Is this G onlybehavior?
            case 0x1802: bd.dump(),       # 0x18 02 - 544 bytes on 2M SSB
            case 0x1803: bd.unhandled(),  # 0x18 03 - 800 bytes lots of 0s adn some GPS near end.  Surrounded by 30, 40, a d0, then 54 an 64 IDs. Was in DV/FM
            case 0x1c00: bd.unhandled(),  # 0x1c 00 - 0x23 bytes NMEA has oocasional $GPGGA, slows or stops when squelch is open on good signal
            case 0x1c01: bd.unhandled(),  # 0x1c 01 - 292 bytes was on 23cm FM
            case 0x1c03: bd.unhandled(),  # 0x1c 03 - 804 bytes was on 2M CW
            case 0x2000: bd.unhandled(),  # 0x20 00 - 40 bytes random data, was on 2.3G USB
            case 0x2001: bd.unhandled(),  # 0x20 01 - 296 bytes was on 23cm FM all 0s
            case 0x2002: bd.unhandled(),  # 0x20 02 - 552 bytes was on 2N CW
            case 0x2003: bd.unhandled(),  # 0x20 03 - 808 bytes was on 2N CW
            case 0x2400: bd.unhandled(),  # 0x24 00 - 88 bytes NMEA data, slow intermittent
            case 0x2401: bd.mode(),       # 0x24 01 - 300 bytes  get on filter change.  Has freq, mode, filt etc
            case 0x2403: bd.dump(),       # 0x24 03 - 812 bytes on 2M SSB
            case 0x2800: bd.unhandled(),  # 0x28 00 - 48 bytes random data  was in 2.3G FM
            case 0x2801: bd.mode(),       # 0x28 01 - 304 bytes  get on filter change in SSB mode, mode changes to RTTY,  has freq, mode and all.
            case 0x2802: bd.dump(),       # 0x28 02 - 560 bytes  on 2M SSB
            case 0x2803: bd.unhandled(),  # 0x28 03 - 816 bytes  was n 5G FM doing PTT 
            case 0x2c00: bd.unhandled()   # 0x2c 00 - 52 bytes follows PTT.  unknown data  NMEA during RX. 
            # this usually has good data but on 2M and 23cm FM at least once it was all zeros
            case 0x2c01: bd.mode(),bd.frequency(), # 0x2c 01 - 308 bytes get on mode change, has frequency data in it both vfos
            case 0x2c03: bd.unhandled()   # 0x2c 03 - ?? bytes was in 2M FM got invalid Mode Filt, DataM values
            case 0x3000: bd.unhandled(),  # 0x30 00 - 56 bytes was in 2.3G FM
            case 0x3001: bd.unhandled(),  # 0x30 01 - 312 bytes NMEA data
            case 0x3002: bd.unhandled(),  # 0x30 02 - 568 bytes was on 2M CW
            case 0x3003: bd.unhandled(),  # 0x30 03 - NMEA data
            case 0x3400: bd.unhandled(),  # 0x34 00 - 0x13 bytes $GNZDA NMEA data, usually 0s
            case 0x3401: bd.unhandled(),  # 0x34 01 - 316 bytes was on 23cm FM
            case 0x3402: bd.unhandled(),  # 0x34 02 - 572 bytes was on 2M CW
            case 0x3403: bd.unhandled(),  # 0x34 03 - 828 bytes 70cm FM spectrum likely
            case 0x3800: bd.unhandled(),  # 0x38 00 - 64 bytes NMEA data,like $GNZDA  mostly 0s, msg rate speeds up in TX
            case 0x3801: bd.unhandled(),  # 0x38 01 - 320 bytes was on 23cm FM
            case 0x3802: bd.unhandled(),  # 0x38 02 - 576 bytes was on 2M CW
            case 0x3c00: bd.unhandled(),  # 0x3c 00 - 68 bytes NMEA, $GPGGA, $GNZDA, $GLGSV  Fast rate during TX
            case 0x3c02: bd.unhandled(),  # 0x3c 02 - 580 bytes was on 2M CW
            case 0x3c03: bd.unhandled(),  # 0x3c 03 - 836 bytes on 70cm FM spectrum likley
            case 0x4000: bd.unhandled(),  # 0x40 00 - 72 bytes NMEA data. On PTT and on band change
            case 0x4001: bd.unhandled(),  # 0x40 01 - 328 bytes was on 23cm FM
            case 0x4003: bd.unhandled(),  # 0x40 03 - 840 bytes 70cm FM spectrum likely
            case 0x4400: bd.unhandled(),  # 0x44 00 - 0x4b bytes NMEA data shows on startup of radio
            case 0x4401: bd.unhandled(),  # 0x44 01 - 332 bytes was on 23cm FM
            case 0x4402: bd.unhandled(),  # 0x44 02 - 332 bytes was on 2M CW
            case 0x4403: bd.unhandled(),  # 0x44 03 - 844 bytes Looks like spectrum data, was in RTTY switched to AM and 23cm to RTTY could be initial screen draw as happens on band change
            case 0x4800: bd.unhandled(),  # 0x48 00 - 80 bytes  Random daa, was on 2.3G USB and 5.7 ATV
            case 0x4801: bd.unhandled(),  # 0x48 01 - 336 bytes  FM and DV mode on 2.3G  all 0s
            case 0x4802: bd.unhandled(),  # 0x48 02 - 584 bytes  on 2M CW
            case 0x4803: bd.unhandled(),  # 0x48 03 - 848 bytes  Unknkown, was in FM and DV\FM, issued on switch from DV to SSB and back to DV, no freq data
            case 0x4c00: bd.unhandled(),  # 0x4c 00 - 84 bytes random data  was in 2.3G FM
            case 0x4c01: bd.unhandled(),  # 0x4c 01 - 356 bytes was in DV/FM all 0s   Spectrum in AM mode  Can visualize teh APRS bursts in the middle of the data range.
                                            #  when spectrum ref is lowered, data becomes 0s and then stops.  Only strong sugs burst packets
            case 0x4c02: bd.unhandled(),  # 0x4c 02 - 596 bytes  USB 2.4G  all zero quiet band
            case 0x4c03: bd.unhandled(),  # 0x4c 03 - 852 bytes  DV\FM, likely spectrum
            case 0x5000: bd.unhandled(),  # 0x50 00 - 88 bytes NMEA data
            case 0x5001: bd.unhandled(),  # 0x50 01 - 344 bytes Showed up in DD mode on 2G, also on 2M SSb a0s
            case 0x5003: bd.unhandled(),  # 0x50 03 - 856 bytes 1 time on TX start, lots of 0 ending with NMEA data
            case 0x5400: bd.unhandled(),  # 0x54 00 - 92 bytes random data  was in 2.3G FM
            case 0x5401: bd.dump(),       # 0x54 01 - 348 bytes NMEA data in DV/FM mode
            case 0x5402: bd.unhandled(),  # 0x54 02 - 604 bytes spectrum likely 70cm FM
            case 0x5800: bd.unhandled(),  # 0x58 00 - 96 bytes random data  was in 2.3G FM
            case 0x5801: bd.unhandled()   # 0x58 01 - 352 bytes was in FM on 5GHz and 2M jsut spectrum or similar
            case 0x5802: bd.unhandled(),  # 0x58 02 - 608 bytes was in FM and SSB spectrum likely
            case 0x5c00: bd.unhandled(),  # 0x5c 00 - 100 bytes was in 2.3G FM
            case 0x5c01: bd.unhandled(),  # 0x5c 01 - 356 bytes was in DV/FM all 0s
            case 0x5c02: bd.unhandled(),  # 0x5c 02 - 612 bytes in AM mode, looks like spectrum  also  on 70cm FM
            case 0x6000: bd.unhandled(),  # 0x60 00 - 104 bytes NMEA data
            case 0x6001: bd.unhandled(),  # 0x60 01 - 360 bytes was on 23cm FM
            case 0x6002: bd.unhandled(),  # 0x60 02 - 616 bytes spectrum likely on 70cm FM
            case 0x6400: bd.unhandled(),  # 0x64 00 - 108 bytes NMEA data
            case 0x6401: bd.unhandled(),  # 0x64 01 - 364 bytes NMEA data - burst of packets
            case 0x6402: bd.unhandled(),  # 0x64 02 - 620 bytes NMEA data - burst of packets
            case 0x6800: bd.unhandled(),  # 0x68 00 - 112 bytes NMEA data.Zeros in DV/FM
            case 0x6801: bd.unhandled(),  # 0x68 01 - 220 bytes was on 23cm FM
            case 0x6802: bd.unhandled(),  # 0x68 02 - 624 bytes ?? 
            case 0x6c00: bd.unhandled(),  # 0x6c 00 - 116 bytes NMEA data
            case 0x6c01: bd.unhandled(),  # 0x6c 01 - 372 bytes was on 23cm FM
            case 0x7000: bd.unhandled(),  # 0x70 00 - 120 bytes NMEA on RX, 0s on TX
            case 0x7001: bd.unhandled(),  # 0x70 01 - 376 bytes Was on 23cm FM
            case 0x7400: bd.unhandled(),  # 0x74 00 - 124 bytes random, was on 2.4g FM
            case 0x7401: bd.unhandled(),  # 0x74 01 - 380 bytes All 0s
            case 0x7402: bd.unhandled(),  # 0x74 02 - 636 bytes On 2M CW
            case 0x7800: bd.unhandled(),  # 0x78 00 - 128 bytes NMEA data 
            case 0x7801: bd.unhandled(),  # 0x78 01 - 120 bytes NMEA on RX, 0s on TX
            case 0x7c00: bd.unhandled(),  # 0x7c 00 - 132 bytes NMEA data
            case 0x7c01: bd.unhandled(),  # 0x7c 01 - 388 bytes was on 23cm FM
            case 0x8000: bd.unhandled(),  # 0x80 00 - NMEA data
            case 0x8001: bd.unhandled(),  # 0x80 01 - 392 bytes was on 23cm FM
            case 0x8002: bd.unhandled(),  # 0x80 02 - 648 bytes was on 70cm changing modes
            #case 0x84: bd.dump(),        # 0x84 xx - ?? bytes ??
            case 0x8800: bd.unhandled(),  # 0x88 00 - 144 bytes mostly 0s
            case 0x8801: bd.unhandled(),  # 0x88 01 - 400 bytes was on 23cm FM
            case 0x8c01: bd.unhandled(),  # 0x8c 01 - 404 bytes was on 23cm FM all 0s
            case 0x8c02: bd.dump(),       # 0x8c 02 - 660 bytes spectrum maybe
            case 0x9001: bd.unhandled(),  # 0x90 01 - 408 bytes spectrum on 2.4G
            case 0x9400: bd.unhandled(),  # 0x?? - ?? bytes shows up periodically, maybe use for timer to log temps
            case 0x9401: bd.unhandled(),  # 0x94 01 - 412 bytes Looks like spectrum on 2.4G SSB
            case 0x9402: bd.unhandled(),  # 0x94 02 - 668 bytes Looks like spectrum
            case 0x9801: bd.unhandled(),  # 0x98 01 - 416 bytes on 23cm FM mostly 0s
            case 0x9802: bd.unhandled(),  # 0x98 02 - 672 bytes spectrum while in 2M FM quiet band
            case 0x9c00: bd.unhandled(),  # 0x9c 00 - 164 bytes saw in DV/FM. nearly all zeros,  rare message.
            case 0x9c01: bd.unhandled(),  # 0x9c 01 - 420 bytes was on 23cm FM
            case 0xa000: bd.unhandled(),  # 0xa0 00 - 168 bytes was on 23cm FM
            case 0xa002: bd.unhandled(),  # 0xa0 02 - 680 bytes Spectrum likely in AM
            case 0xa400: bd.unhandled(),  # 0xa4 00 - 172 bytes shows in DV/FM mode. Looks like GPS data.  Codl just be gps mixed in
            case 0xa401: bd.unhandled(),  # 0xa4 01 - 428 bytes shows in DV/FM mode. All 0s
            case 0xa406: bd.unhandled(),  # 0xa4 06 - 1448 bytes go in 2M at radio startup - first message maybe has startup stuff we need
            case 0xa800: bd.dump(),  # 0xa8 00 - 176 bytes 2.4G all zeros no signal
            case 0xa801: bd.unhandled(),  # 0xa8 01 - 488 and 432 bytes shows in DV/FM when ref level raised and APRS signal and on 2.4G
            case 0xa802: bd.unhandled(),  # 0xa8 02 - 688 and 432 bytes shows in DV/FM when ref level r
            case 0xa803: bd.frequency(),  # 0xa8 03 - 944 bytes shows in FM after a radio restart  3rd startup message
            case 0xac00: bd.unhandled(),  # 0xac 00 - 180 bytes All 0s
            case 0xac01: bd.unhandled(),  # 0xac 01 - 436 bytes on 2M USB
            case 0xac02: bd.dump(),       # 0xac 02 - 692 bytes 2M FM spectrum likely
            case 0xb000: bd.unhandled(),  # 0xbo 00 - 184 bytes was on 23cm FM
            case 0xb001: bd.unhandled(),  # 0xbo 01 - 440 bytes was on 23cm FM
            case 0xb002: bd.unhandled(),  # 0xbo 02 - 696 bytes on 5G FM/ or DV 
            case 0xb003: bd.unhandled(),  # 0xbo 03 - 952 bytes shows on radio startup, mostly zero filled
            case 0xb400: bd.unhandled(),  # 0xb4 00 - 188 bytes  was on 2M CW all 0s
            case 0xb401: bd.unhandled(),  # 0xb4 01 - 444 bytes was pon 23cm Al l0s
            case 0xb402: bd.unhandled(),  # 0xb4 02 - 700 bytes  spectrum maybe on 2M FM after startup
            case 0xb403: bd.unhandled(),  # 0xb4 03 - 956 bytes  spectrum maybe on 2M FM after startup - 5th startup msg
            case 0xb800: bd.unhandled(),  # 0xb8 00 - 192 bytes  On 2M SSB
            case 0xb801: bd.unhandled(),  # 0xb8 01 - 448 bytes  2.4G band SSB all zeros quiet band, same for 23cm FM
            case 0xb802: bd.unhandled(),  # 0xb8 02 - 704 bytes  spectrum likely
            case 0xbc00: bd.unhandled(),  # 0xbc 00 - 196 bytes  was on 2M CW
            case 0xbc01: bd.unhandled(),  # 0xbc 01 - 452 bytes  was on 23cm FM all zeros
            case 0xc000: bd.unhandled(),  # 0xc0 00 - 200 bytes  was on 23cm FM
            case 0xc001: bd.unhandled(),  # 0xc0 01 - 488 bytes  was in DV/FM msotly 0s nmea data
            case 0xc002: bd.unhandled(),  # 0xc0 02 - xx bytes  was in DV/FM msotly 0s nmea data
            case 0xc003: bd.unhandled(),  # 0xc0 02 - 788 bytes  was on 2M CW
            case 0xc400: bd.unhandled(),  # 0xc4 00 - 204 bytes  RTTY spectrum/GPS maybe
            case 0xc401: bd.unhandled(),  # 0xc4 01 - 460 bytes  On 2M SB
            case 0xc402: bd.unhandled(),  # 0xc4 02 - 716 bytes  was in DV/FM mostl;y 0s, some nmea
            case 0xc800: bd.unhandled(),  # 0xc8 00 - 208 bytes  RTTY on 23cm spectrum maybe
            case 0xc801: bd.unhandled(),  # 0xc8 01 - 464 bytes  was in DV/FM mosty all zeros, maybe spectrum
            case 0xcc00: bd.unhandled(),  # 0xcc 00 - 212 bytes  was on 23cm FM all 0s mostly
            case 0xcc01: bd.unhandled(),  # 0xcc 01 - 468 bytes  was on 23cm FM all 0s mostly
            case 0xcc02: bd.unhandled(),  # 0xcc 02 - 724 bytes  2M FM  spectrum
            case 0xd000: bd.unhandled(),  # 0xd0 00 - 216 bytes ???PTT start event???, freq at 0xb8 for current VFO.  Works on simplex, duplex, no split, no VFOb data
            case 0xd001: bd.unhandled(),  # 0xd0 01 - 472 bytes 5G DD mode   all 0s
            case 0xd400: bd.case_xD4(),   # 0xd4 00 - 220 bytes get Split msg on d4-00 has frequency but this is short msg
            case 0xd401: bd.unhandled(),  # 0xd4 01 - 476 bytes Mostly zeros, came after a PTT event
            case 0xd402: bd.unhandled(),  # 0xd4 02 - 732 bytes Mostly zeros on 70cm switching FM to SSB folowing d400 mode change
            case 0xd800: bd.frequency(),  # 0xd8 00 - 224 bytes data for freq, mode and more
            case 0xd801: bd.unhandled(),  # 0xd8 01 - 480 bytes All zeros on 23cm FM
            case 0xdc00: bd.unhandled(),  # 0xdc 00 - 228 bytes rarely shows, has NMEA data in it showed when ref level raised on 2.4G
            case 0xdc01: bd.unhandled(),  # 0xdc 01 - 484 bytes was on 2M FM
            case 0xe000: bd.unhandled(),  # 0xe0 00 - 232 bytes was on 23cm FM
            case 0xe001: bd.unhandled(),  # 0xe0 01 - 488 bytes in FM spectrum on band change to 23cm
            case 0xe002: bd.unhandled(),  # 0xe0 02 - 744 bytes in DV/FM spectgrum+GPS data - 4th startup message
            case 0xe400: bd.unhandled(),  # 0xe4 00 - 236 bytes was on 23cm FM
            case 0xe401: bd.unhandled(),  # 0xe4 01 - 492 bytes shows when activity on spectrum was in DV
            case 0xe402: bd.unhandled(),  # 0xe4 02 - 748 bytes was on 2M CW
            case 0xe800: bd.ptt(),        # 0xe8 00 - 240 bytes tx/rx changover trigger, e801 normal RX or TX state.  PTT is last byte but may be in others also. Byte 0xef is PTT state
            case 0xe801: bd.dump(),       # 0xe8 01   496 bytes is spectrum data on RX when enabled 0
            case 0xe802: bd.unhandled(),  # 0xe8 02   752 bytes was on 2.4G FM
            case 0xec00: bd.frequency(),  # 0xec 00 - 244 bytes occurs on data-mode (digital mode) change
            case 0xec02: bd.unhandled(),  # 0xec 02 - 0x133 bytes filled with zeros and blocks of gps data
            # the 04, 54, 64 f4, fc ID showed up when there was a signal in DV/FM listeing to packet.  Filled with 0s.  WIl lalso show up when a signal is off freq
            case 0xf000: bd.unhandled(),  # 0xf0 00 - 248 bytes was in DV mode. Looks like spectrum.  had squelch on in FM
            case 0xf001: bd.unhandled(),  # 0xf0 01 - 504 bytes was in DV mode. Looks like spectrum.  had squelch on in FM
            case 0xf002: bd.unhandled(),  # 0xf0 02 - ??bytes was in DV mode.
            case 0xf400: bd.unhandled(),  # 0xf4 00 - 252 bytes NMEA data shows up when a large signal was on teh spectgrum and the ref line was < 0 which squelces f4 02 in DV mode.
            case 0xf402: bd.unhandled(),  # 0xf4 02 - 764 bytes NMEA data at end, looks like spectrum in DV mode.  Stops when ref line <0
            case 0xf800: bd.unhandled(),  # 0xf8 00 - 255 bytes shows up periodically in middle of TX streams and other times
            case 0xf801: bd.unhandled(),  # 0xf8 01 - 512 bytes was on 2M CW
            case 0xfc00: bd.unhandled(),  # 0xfc 00 - 260 bytes Looks like spectrum/NMEA data.  Saw in many palces, during TX, in FM to SSB transition, DV/FM            
            case _: bd.case_default()     # anything we have not seen yet comes to here


    def switch_case(self, payload, payload_len):
        bd.payload_copy = payload
        bd.payload_ID_byte = payload[0x0001]
        bd.payload_Attrib_byte = payload[0x0002]
        bd.payload_len = payload_len
        bd.payload_ID = (bd.payload_ID_byte << 8)+bd.payload_Attrib_byte

        # Turn off all lines below this to see only hex data on screen
        #if (bd.payload_ID == 0xa4):   # a0 a4 a8 ac
         #   bd.hexdump(payload)
         #   print(bd.payload_len, "\n")

        # Turn this print ON to see all message IDs passing through here
        #print("Switch on 0x"+format(bd.payload_ID,"04x")+"  Len:", format(bd.payload_len))

        #Turn this on to only see hex dumps for any and all packets
        #bd.dump()

        # most large payloads are spectrum data and we can ignore those.
        if (bd.payload_len < 360 or bd.payload_ID == 0xa803): # and bd.payload_ID != 0xe801):
           self.switch(bd.payload_ID)

        # reset the storage to prevent memory leaks
        bd.payload_copy = None
        bd.payload_ID_byte = None
        bd.payload_Attrib_byte = None
        bd.payload_len = None
        bd.payload_ID = None


#--------------------------------------------------------------------
#  Read config file
#--------------------------------------------------------------------

def read_config(config_file):
    global dht11_enable
    global dht11_poll_time

    try:
        with open(config_file,"r") as file:
            key_value_pairs = {}
            current_key = None
            current_value = None
            for line in file:
                line = line.strip()
                # Check if the line is empty or a comment (starts with #)
                if not line or line.startswith('#'):
                    # Skip this line
                    continue
                # Check if the line starts with a tab character
                elif line.startswith('\t'):
                    # Check if we have a current key and value
                    if current_key is not None and current_value is not None:
                        # Append the line to the current value
                        current_value += '\n' + line.lstrip()
                    else:
                        # Log an error and skip this line
                        print(f"Error: Invalid line format - {line}")
                        continue
                else:
                    # Check if we have a current key and value
                    if current_key is not None and current_value is not None:
                        # Add the current key-value pair to the dictionary
                        key_value_pairs[current_key] = current_value
                    # Split the line into key and value
                    key_value = line.split('=', 1)
                    if len(key_value) != 2:
                        # Log an error and skip this line
                        print(f"Error: Invalid line format - {line}")
                        continue
                    # Set the current key and value
                    current_key = key_value[0].strip()
                    current_value = key_value[1].strip()
            # Check if we have a current key and value
            if current_key is not None and current_value is not None:
                # Add the current key-value pair to the dictionary
                key_value_pairs[current_key] = current_value
            # Return the dictionary of key-value pairs
            #print(key_value_pairs)
            return key_value_pairs

    except FileNotFoundError:
            print(f"The file {config_file} does not exist in the home directory.")
            bd.write_band(bd.vfoa_band)
    except Exception as e:
            print(f"An error occurred: {e}")

#  __________________________________________________________________
#
#   Packet Capture and Filtering
#  __________________________________________________________________
#
def parse_packet(payload):
    #print(payload)
    #bd.hexdump(payload)
    payload_len = len(payload)
    #print("Payload Length = ", payload_len)

    if (payload_len > 16):
        mh.switch_case(payload, payload_len )  # this extracts and routes messages to functions


def tcp_sniffer(args):
    try:
        # read from piped data input
        total_len = 0
        payload = 0
        payload_len = 0
        header_len = 0
        
        while (1):

            #tcpdump_running = sub.run(['pgrep','tcpdump'], stdout=sub.PIPE).stdout.decode('utf-8').strip()  # check if tcpdump already running

            if (1): #not tcpdump_running:
                # This one filters out more, no spectrum stuff
                tcpdump_command = ['sudo','tcpdump','-nlvi','eth0','-A','-x','tcp dst port 50004 and greater 229 and less 1100']
                #tcpdump_command = ['sudo','tcpdump','-n','-l','-v','-i','eth0','-A','-x','dst','port','50004','and','tcp','and','greater','229']   #,'or','arp']
                # This one includes the other direction which includes spectrum stuff, especially 0xe801.
                #tcpdump_command = ['sudo','tcpdump','-n','-l','-v','-i','eth0','-A','-x','port','50004','and','tcp','and','greater','229']
                p = sub.Popen(tcpdump_command, stdout=sub.PIPE, text=True)  #, stderr=sub.PIPE)
                payload_str = ""
                payload_line = ""
                # loops in here continuously acting on new messages
                for row in iter(p.stdout.readline, b''):
                #line = p.stdout.readline().strip()
                    #print(row)
                    if row.isspace():
                        print("Empty line") 
                    line = row.strip(" \n\r\t()")
                    #print(line)
                    # determine if this is a info line or data line
                    # if info line, extract the total and payload lengths
                    r = line.find("0x",0,4)  # data lines start woth spaces and 0xNNNN
                    d = line.find(":",2,4)  # test for 1st line of new packet
                    #print("r=",r, " d=",d)
                    if (d != -1 and r == -1):  # info line
                        total_len = int(line.rsplit("length ")[1])   # the length value is at the end inside ()
                        #print("total_len=",total_len)  # extracted the total packet length
                    elif (d == -1 and r == -1):  # 2nd line
                        payload_len = int(line.rsplit("length ")[1])
                        #print("payload_len=", payload_len)  #extracted the payload length
                        header_len = total_len - payload_len  # calc the header length to get our data start index
                        #print("total length = ", total_len, "payload length = ", payload_len, "header length = ", header_len)
                    elif (r != -1):  # skip non-payload lines
                        payload_raw = line.strip(" x:")[7:]   # str   8 groups of 2 bytes
                        payload_raw = payload_raw.split()
                        #print("payload_raw = ", payload_raw)
                        separator = ""
                        payload_line = separator.join(payload_raw)[0:]  #  remove white spaces
                        #print("line = ", payload_line)
                        payload_str = payload_str + payload_line   # str
                        #print("byte count = ", len(payload_str)/2, "total expected", total_len)

                        # finished collecting last line now process it, strip off the TCP header
                        if (len(payload_str)/2 >= total_len):
                            payload_str = payload_str #[header_len:total_len]
                            #print("str="+payload_str)
                            payload = bytes.fromhex(payload_str)[header_len:total_len]  # bytes - strip tcpheader info
                            #print("payload size calcutated = ", len(payload), " payload expected = ", payload_len)
                            #print(payload)
                            parse_packet(payload)  #  process our new message
                            payload = 0
                            payload_str = ""


    except KeyboardInterrupt:
        bd.write_split(bd.split_status)
        bd.write_band(bd.vfoa_band)
        print('Done')
        dht.stop()
        #dc.stop()

    finally:
        GPIO.cleanup()
        sys.exit()


if __name__ == '__main__':
    #import sys
    io = OutputHandler()  # instantiate our classes
    bd = BandDecoder()
    mh = Message_handler()
    print("TCP905 V3  - Ethernet Band Decoder for the IC-905 - K7MDL Feb 2025")
    tim = dtime.now()
    print("Startup at", tim.strftime("%m/%d/%Y %H:%M:%S%Z"), flush=True)
    io.gpio_config()
    
    split_file = os.path.expanduser("~/.Decoder905.split")  # saved state for last known split status
    if not os.path.exists(split_file): 
        bd.write_split(0)
    radio_split = read_config(split_file)
    bd.read_split(radio_split)
       
    band_file = os.path.expanduser("~/.Decoder905.band")    # last known band value
    if not os.path.exists(band_file): 
        bd.write_band("2M")
    radio_band = read_config(band_file)
    bd.read_band(radio_band)
    
    # read in config, split and band files
    config_file = os.path.expanduser("~/Decoder905.config")
    key_value_pairs = read_config(config_file)
    bd.init_band(key_value_pairs)
    
    # Update the temperature log
    bd.write_temps("Program Startup\n")
    dht = RepeatedTimer(dht11_poll_time, bd.temps)
    
    # Start the main program
    #dc = DecoderThread(tcp_sniffer(sys.argv))   # option to run main program in a thread
    tcp_sniffer(sys.argv)
    #  Program never returns here
    io = None
    bd = None
    mh = None
