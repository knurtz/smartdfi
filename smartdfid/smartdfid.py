#!/usr/bin/env python
# -*- coding: utf-8 -*-
# make sure file is utf-8: ßöäü

import logging
import logging.handlers
# import argparse		# for command line parsing
import sys
import time
import socket
import re			# regular expressions
import json
import smart_dfi_display       # needed for serial communication between computer and display controller (LAFIS)

# =============== SETTINGS ==========================

LOG_FILENAME = "/home/display/smartdfi/smartdfid/logfile.txt"
LOG_LEVEL = logging.INFO  			# Could be "INFO",  "DEBUG" or "WARNING"

HOST = "localhost"
PORT = 12581					# smartdfid: 12581, gpiod: 12582, msggend: 12583

TX_PORT = "/dev/ttyUSB1"
RX_PORT = "/dev/ttyUSB0"

DISPLAY = smart_dfi_display.Display(tx_port = TX_PORT, rx_port = RX_PORT, address = 2)
# =============== FUNCTION DEFINITIONS ======================

def check_protocol(d):
	"""Check if the given JSON complies with the protocol for smartdfid. Returns tuple like (success [bool], messages [string])."""

	if not isinstance(d, list):
		return (False, "Content must be a list.")

	if len(d) == 0:	# empty telegram, only update requested
		return (True, "")
	
	# if content is not empty, check for each field, if values are valid
	for field in d:
		
		# check for violations that result in quitting the execution:
		if not isinstance(field, dict):
			return (False, "At least one field in content list is not a dictionary.")
		
		if not "line" in field:
			return (False, "At least one content field does not have a line number.")

		if not isinstance(field["line"], int) or field["line"] not in range(1,6):
			return (False, "At least one line number is incorrect.")
		
		if not "text" in field:
			return (False, "At least one content field does not have a text field.")

		if not isinstance(field["text"], basestring) or field["text"] == "":
			return (False, "At least one text field is empty or not a string.")
	
	# no errors found? return name of client and success
	return (True, "")



def create_field_telegram(d):
	"""Take the content list from the protocol and return a LAFIS field telegram that can then be sent to the display."""
	# this list will contain all single fields for each line, with which we can then forge a field telegram
	field_list = []
	
	# go through each line of the content
	for l in d:
		doubletext = False
		# fill fields with default values if they do not exist or contain incorrect values
		if l["text"] == "":
			l["text"] == " "
		if not "font" in l or l["font"] not in ["P", "B", "S", "N"]:
			l["font"] = "P"
		if not "align" in l or l["align"] not in ["L", "M", "R", "D"]:
			l["align"] = "L"
		if l["align"] == "D":
			# if doubletext is requested, check additional fields, reset font variable and save for later
			l["align"] = "L"
			doubletext = True
			if not "text2" in l or l["text2"] == "":
				doubletext = False		      # no second text? switch back to normal left aligned mode
			if not "font2" in l or l["font2"] not in ["P", "B", "S", "N"]:
				l["font2"] = "P"
	
		# check additional field for blinktext
		if not "blinktime" in l or l["blinktime"] not in range(0,31) or not isinstance(l["blinktime"], int):
			l["blinktime"] = 0

		if l["blinktime"] != 0:
			field_list.append(DISPLAY.create_switch_field(line_number = l["line"], text1 = l["text"], text2 = " ", time = str(l["blinktime"]), align = l["align"], font = l["font"]))
			continue

		# no blinktext? -> create a normal text field
		field_list.append(DISPLAY.create_field(line_number = l["line"], text = l["text"], align = l["align"], font = l["font"]))
		
		# doubletext? -> add an additional text field
		if doubletext:
			field_list.append(DISPLAY.create_field(line_number = l["line"], text = l["text2"], align = "R", font = l["font2"]))
	
	return DISPLAY.create_field_telegram(field_list)		


# =============== CONFIGURE LOGGING ==========================

# configure logger
logger = logging.getLogger("smartdfid_logger")
logger.setLevel(LOG_LEVEL)

# Make a handler that writes to a file, making a new file at midnight and keeping 3 backups
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=3)

# Format each log message like this
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')

handler.setFormatter(formatter)
logger.addHandler(handler)

# Make a class we can use to capture stdout and sterr in the log
class MyLogger(object):
        def __init__(self, logger, level):
                """Needs a logger and a logger level."""
                self.logger = logger
                self.level = level

        def write(self, message):
                # Only log if there is a message (not just a new line)
                if message.rstrip() != "":
                        self.logger.log(self.level, message.rstrip())

# Replace stdout and stderr with logging to file at INFO/ERROR level
sys.stdout = MyLogger(logger, logging.INFO)
sys.stderr = MyLogger(logger, logging.ERROR)

logger.info("Starting smartdfid daemon.")
DISPLAY.transmit_telegram(create_field_telegram([{"line": 1, "text": "SmartDFI ready"}]))


# =============== SET UP SOCKET SERVER ==========================
	
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
logger.debug("Socket created")
 
try:
    s.bind((HOST, PORT))
except socket.error, msg:
    logger.error("Bind failed. Error Code: " + str(msg[0]) + " Message: " + msg[1])
    sys.exit()
 
s.listen(0)  # only one connection at the same time
logger.info("Socket now listening")

# ============= begin endless loop waiting for connections ======

while True:
	s.settimeout(None)	# wait infinitely long for incoming connections 
	conn, addr = s.accept() # wait to accept a connection - blocking call

	logger.debug("Connected with " + addr[0] + ":" + str(addr[1]))

	conn.settimeout(5)	# allow the new connection a timeout of 5 seconds for all blocking operations
	try:
		rec_buffer = conn.recv(4096)			# receive JSON from client
	except:
		conn.sendall("NAK")
		conn.close()
		continue
	
	# check if data is valid JSON
	try:
		client_data = json.loads(rec_buffer)
	except:
		logger.error("No valid JSON received from client. Closing connection")
		conn.sendall("NAK") 	# send NAK and close connection
		conn.close()
		continue		# go back to listening for incoming connections

	# check protocol conformity 
	(result, msg) = check_protocol(client_data)
	if not result:
		logger.error("Protocol violation: " + msg + " Closing connection.")
		conn.sendall("NAK")
		conn.close()
		continue

	# create a field telegram
	field_telegram = create_field_telegram(client_data)
	DISPLAY.transmit_telegram(field_telegram)
	
	conn.sendall("ACK")
	conn.close()
