#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file defines the Display class which is used to dricetly communicate with the DFI display to show and remove text

import serial       # needed for serial communication between computer and display controller (LAFIS)

class Display:

    def __init__(self, tx_port = "/dev/ttyUSB_hub1", rx_port = "/dev/ttyUSB_hub2", address = 2):
        """This class is used for low level communication with the DFI controller over serial communications.
        The address is the number that is set at the display's DIP switch, so it is the display's transmit address. When sending data TO it, remember to use address + 1!
        """

        # only allow a valid address
        if address > 30 or address < 2:
            print("[Error] Invalid address given for new Display object")

        self.send_address_str = str(address)
        self.rec_address_str = str(address + 1)

        if len(self.send_address_str) == 1:
            self.send_address_str = "0" + self.send_address_str

        if len(self.rec_address_str) == 1:
            self.rec_address_str = "0" + self.rec_address_str

        if not len(self.send_address_str) == 2:
            print("[Error] Address not correct for new Display object")

        if not len(self.rec_address_str) == 2:
            print("[Error] Address not correct for new Display object")


        self.tx_channel = serial.Serial()
        self.rx_channel = serial.Serial()

        try:
            self.tx_channel = serial.Serial(port = tx_port, baudrate = 9600, bytesize = serial.EIGHTBITS, parity = serial.PARITY_EVEN, stopbits = serial.STOPBITS_ONE)
        except:
            print("[Error] Could not initialize transmitting serial port for new Display object")

        try:
            self.rx_channel = serial.Serial(port = rx_port, baudrate = 9600, bytesize = serial.EIGHTBITS, parity = serial.PARITY_EVEN, stopbits = serial.STOPBITS_ONE, timeout = 5)
        except:
            print("[Error] Could not initialize receiving serial port for new Display object")



	return None


    def replace_charset(self, text):
	
	# conversion happens in latin1 encoding
	text = text.encode('latin1')

	# create charset table
	charset = {
		"\xe4": "\x84",		# ä
		"\xf6": "\x94",		# ö
		"\xfc": "\x81",		# ü
		"\xc4": "\x8e",		# Ä
		"\xd6": "\x99",		# Ö
		"\xdc": "\x9a",		# Ü
		"\xdf": "\xe1"		# ß
	}

	for i, j in charset.iteritems():
        	text = text.replace(i, j)

    	return text
    

    def transmit_telegram(self, content):
        """This establishes a connection with the display, takes a telegram (complete with start, stop and XOR bytes) and transmits it over the current tx_channel. Checks for basic errors and responses from the display.
        """

        # check if we could establish an outgoing serial connection
        if not self.tx_channel.isOpen() or not self.rx_channel.isOpen() or not isinstance(content, basestring):
		print "[smart_dfi_display] ERROR - Required serial channels are not established."
        	return False

        print ("[smart_dfi_display] DEBUG - Starting transmit")

        # remove all remedies from past transactions
        self.rx_channel.flushInput()

        # first, contact the display by sending the header [SOH][Address1][Address2][ENQ]
        self.tx_channel.write("\x04")   # reset connection
        self.tx_channel.write("\x01" + self.rec_address_str + "\x05")

        print ("[smart_dfi_display] DEBUG - Transmitted header")

        # check if display responds with [DLE]0
	resp = self.rx_channel.read(2) 
	if not resp == "\x10\x30":    # reads two bytes from serial channel until it timeouts
       		print ("[smart_dfi_display] ERROR - Received no response from display. Received: " + self.str2ord(resp))
           	return False

        print("[smart_dfi_display] DEBUG - Received response from display.")

        transmitted_bytes = self.tx_channel.write(content)

        if transmitted_bytes == len(content):
        	print("[smart_dfi_display] DEBUG - Transmitted content successfully")
        else:
		print("[smart_dfi_display] ERROR - Some bytes got lost.")
	        return False
	resp = self.rx_channel.read(2) 
	if not resp == "\x10\x31":
	        print("[smart_dfi_display] ERROR - No acknowledge from display after successfully sending data. Received: " + self.str2ord(resp))
        else:
        	print("[smart_dfi_display] DEBUG - Data acknowledged by display.")

        self.tx_channel.write("\x04")

        return True

	
    def str2ord(self, s):
	r = ""
	for c in s:
		r = r + str(ord(c))
	return r


    def create_field(self, line_number, text, align = "L", font = "P", start="01", length="03"):
        """This function will forge a new "Feld", which contains the text infomation for one line, ending with the [ETB] character"
        """

        # some error handling first

        if line_number < 1 or line_number > 5:
            print("[smart_dfi_display] ERROR - Could not write text, wrong line number given.")
            return False

        if not isinstance(text, basestring) or text == "":
            print("[smart_dfi_display] ERROR - Invalid text field. To write an empty line, simply transmit a single space character.")
            return False

        if not align in ["L", "R", "M"]:
            print("[smart_dfi_display] ERROR - Could not write text, align needs to be either L, R or M")
            return False

        if not font in ["P", "B", "S", "N"]:
            print("[smart_dfi_display] ERROR - Could not write text, font needs to be either P, B, S or N")
            return False

	if not start in ["01", "02", "03"]:
	    print("[smart_dfi_display] ERROR - Start number must be a string and either \"01\", \"02\" or \"03\"!")
	    return False
	
	if not length in ["01", "02", "03"]:
	    print("[smart_dfi_display] ERROR - Length must either be \"01\", \"02\" or \"03\"!")
	    return False

	# convert umlauts to hex codes
	text = self.replace_charset(text)

	# beginn telegram as shown in the documentation. S stands for static text,the "01" is not evaluated
	content = "0" + str(line_number) + start + length + align + font + "S01"
	content = content.encode('latin1')
	
        # now add the text
        content += text
	
	# end of field
        content += "\x17"

        return content


    def create_switch_field(self, line_number, text1, text2, time, align = "L", font = "P", start="01", length="03"):
        """This function will forge a new "Feld", which contains the text infomation for one line, ending with the [ETB] character"""

        # some error handling first
        if line_number < 1 or line_number > 5:
            print("[smart_dfi_display] ERROR - Could not write text, wrong line number given")
            return False

        if not isinstance(text1, basestring) or text1 == "" or not isinstance(text2, basestring) or text2 == "":
            print("[smart_dfi_display] ERROR - Invalid text field. To write an empty line, simply transmit a single space character.")
            return False

        if not align in ["L", "R", "M"]:
            print("[smart_dfi_display] ERROR - Could not write text, align needs to be either L, R or M")
            return False

        if not font in ["P", "B", "S", "N"]:
            print("[smart_dfi_display] ERROR - Could not write text, font needs to be either P, B, S or N")
            return False

	if not start in ["01", "02", "03"]:
	    print("[smart_dfi_display] ERROR - Start number must be a string and either \"01\", \"02\" or \"03\"!")
	    return False
	
	if not length in ["01", "02", "03"]:
	    print("[smart_dfi_display] ERROR - Length must either be \"01\", \"02\" or \"03\"!")
	    return False

	# convert umlauts to hex codes
	text1 = self.replace_charset(text1)
	text2 = self.replace_charset(text2)

	# beginning of telegram sets line number and font stuff
        content = "0" + str(line_number) + start + length + align + font + "B" + time
	content = content.encode('latin1')

        # now add the text
        content += text1 + "\x1a" + text2

        content += "\x17"

        return content



    def create_field_telegram(self, fields):
        """This function takes one ore more fields as created by the create_field function and merges them into one field telegram.
        """

        # content = "1"               # select the front side
        # content += "\x30"           # do nothing to the relais, since we don't use it
        # content += 5 * "\x30"       # 5 reserved bytes
        # content += "F"              # indicates a "Feld" telegram

        content = "1\x30" + 5 * "\x30" + "F"

        for item in fields:
            content += item

        content += "\x03"             # end the telegram

        # calculate the XOR checksum of the telegram
        checksum = 0
        for char in content:
            checksum ^= ord(char)

        content = "\x02" + content + chr(checksum)        # append start byte (not included in checksum) and checksum to message

        print("[smart_dfi_display] DEBUG - Forged new Feld telegram")

        # format the created telegram for printing
        string = ""
        for char in content:
            if ord(char) < 0x10:
        	string += "0" + str(hex(ord(char)))[2:]
      	    else:
		string += str(hex(ord(char)))[2:]
	
	# print message
	# print(string)

        return content



# in case this file is run on its own, give a short notice on the command line
if __name__ == "__main__":
    print("Please do not start this file on its own but rather import it in your project")
