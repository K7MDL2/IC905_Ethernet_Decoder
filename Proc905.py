#!/usr/bin/env python
import sys
import binascii

band_name = ""
  
#  These band edge values are based on the radio message VFO
#    values which have no offset applied
#  We use this value then once we know the band we can add the
#    fixed offset and then display the actual dial frequency

#  The 10G band values in this table are just dummy values until
#    the 10G transverter is hooked up to observe the actual values

Freq_table = { '2M':{
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


TX = "01"
RX = "00" 
    
# test data
#f = open('/mnt/usbdrive/output/data.txt', 'r')
i=0
freq_last = 0
dial_freq = 0
offset = 0
            
try:
	#  for line in f:
  	while 1:
		line = sys.stdin.readline()
		i=i+1
		#print(line)
		
		# watch for PTT value changes
		ptt_state = line.find("0x0120:", 0)
		if ptt_state != -1:
			ptt_state = line.find(TX, 17, 19)
			if ptt_state != -1:
				print("Band", band_name, " ptt_state is TX ", line)
				# Call GPIO here
			
			ptt_state = line.find(RX, 17, 19)
			if ptt_state != -1:
				print("Band", band_name, " ptt_state is RX ", line)
				# Call GPIO here
		
		# Compute what Band we are
		else:   
			#Extract the 4 byte frequency value
			ptt_state = line.find("0x00e0:", 0)
			if (ptt_state != -1):
				result = line.split()
				#print (result[7],result[8])  
				
				# Convert to hex string
				separator = ""
				freq_hex_str = separator.join(result)[31:]
				#print(freq_hex_str)
				
				# Flip from big to little endian
				byte_array = bytes.fromhex(freq_hex_str)
				little_endian_bytes = byte_array[::-1]
				little_endian_hex_str = little_endian_bytes.hex()
				freq = int(little_endian_hex_str, base=16)
				# Now we have a decimal frequency
			
				# Look for band changes
				if (freq != freq_last):
					# We changed frequencies - print it and do something with GPIO
					#print("\nReceived Uncorrected Frequency Value is ", freq)
					freq_last = freq
					
					# Search the Freq_table to see what band these values lie in
					for band_name in Freq_table:
						if (freq > Freq_table[band_name]['lower_edge'] and
							freq < Freq_table[band_name]['upper_edge'] ):
							# Found a band match, print out the goods
							offset = Freq_table[band_name]['offset'] 
							dial_freq = freq + offset
							print("Band = ", band_name, "    Dial Frequency = ", dial_freq,
								"\n   Lower edge = ", Freq_table[band_name]['lower_edge'] + offset,
								"  Upper edge = ", Freq_table[band_name]['upper_edge'] + offset,
									"     Offset = ", offset)
							# call GPIO here
							break
                
except KeyboardInterrupt:
 	print('Done', i)
# f.close()
