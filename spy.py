#!/usr/bin/env python
import sys

TX = "01"
RX = "00" 
    
# test data
#f = open('/mnt/usbdrive/output/data.txt', 'r')
i=0
try:
#  for line in f:
  while 1:
    line = sys.stdin.readline()
    i=i+1
    result = line.split()
    print (line)    
    
    ptt_state = line.find("0x0120", 0)
    
    if ptt_state != -1:
      ptt_state = line.find(TX, 17)
      if ptt_state != -1:
          print("ptt_state is TX")
      
      ptt_state = line.find(RX, 17)
      if ptt_state != -1:
          print("ptt_state is RX")
    
    # process other line and comnmands    
        
        
except KeyboardInterrupt:
 print('Done', i)
# f.close()
