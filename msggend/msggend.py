#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import logging.handlers
import sys
import datetime
import time
import socket
import re			# regular expressions
import json
import requests			# simple http requests

# =============== SETTINGS ==========================

LOG_FILENAME = "/home/display/smartdfi/msggend/logfile.txt"
LOG_LEVEL = logging.INFO 			# Could be "INFO",  "DEBUG" or "WARNING"

HOST = "localhost"
PORT = 12583					# smartdfid: 12581, gpiod: 12582, msggend: 12583

MODE = "statisch"

# =============== FUNCTION DEFINITIONS ======================

def request_departures():
	array = []
	payload = {"stopid": "33000131", "limit": 15}	# hard coded stop id for Reichenbachstraße

	try:
		r = requests.post("http://webapi.vvo-online.de/dm?format=json", data=payload)	
	except:
		return [{"line":1, "text":"Server nicht erreichbar"}]
	
	if r.status_code != 200:
		return [{"line":1, "text":"Anfrage fehlgeschlagen"}]	
	
	deps = {}
	try:
		deps = r.json()
		deps = deps["Departures"]
	except:
		return [{"line":1, "text":"Fehlerhafte Daten"}]

	now = datetime.datetime.now()
	dfi_line = 1
	logger.debug("Number of results from server: " + str(len(deps)))
	for d in deps:
		
		if "RealTime" in d: 			
			time_str = d["RealTime"]
		elif "ScheduledTime" in d:
			time_str = d["ScheduledTime"]
		else:
			logger.info("One departure was missing both RealTime and ScheduledTime field")
			continue
		
		try:
			time = datetime.datetime.fromtimestamp(int(time_str[6:-10]))
		except:
			logger.info("Could not decode time for one departure")
			continue

		diff_min = int((time - now).total_seconds() / 60)

		if "LineName" in d:
			line_name = d["LineName"]  # this contains the line number as a string, d not confuse with dfi line, which refers to text rows
		else:
			logger.info("One departure was missing its LineName")
			continue

		try:
			line_number = int(line_name)	# try to convert to Integer for comparison later on
		except:
			line_number = 0			# setting this to zero means, that this entry will always pass the check for line number below 99 later.

		if "Direction" in d:
			direction = d["Direction"]	# this contains the destination
		else:
			logger.info("One departure was missing its Direction")
			continue

		if diff_min < 7 or line_number > 99:
			continue	# only display certain results
			
		# if line_number < 10:
		#	line_name = " " + line_name     # align numbers to the right. only looks good if the special character for three empty cols is inserted instead of space -> fix encoding issue first

		array.append({"line": dfi_line, "align": "D", "text": line_name + " " + direction, "text2": str(diff_min)})

		dfi_line += 1 

		if dfi_line > 4:
			break
	
	array.append({"line":5, "align":"L", "text":"Reichenbachstr."})
	return array
		

# =============== CONFIGURE LOGGING ==========================

# configure logger
logger = logging.getLogger("msggend_logger")
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

# Replace stdout and stderr with logging to file at DEBUG/ERROR level
sys.stdout = MyLogger(logger, logging.DEBUG)
sys.stderr = MyLogger(logger, logging.ERROR)

logger.info("Starting msggend daemon.")

# ============= CONFIGURE SOCKETS =================

inc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)		# socket for incoming connection from cron or user
inc.settimeout(None)
inc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

logger.debug("Incoming Socket created")

try:
	inc.bind((HOST,PORT))
except socket.error, msg:
	logger.error("Bind failed. Error Code: " + str(msg[0]) + " - Error Message: " + msg[1])
	sys.exit()

inc.listen(0)
logger.info("Now listening")

while(True):
	conn, addr = inc.accept()	# blocking call

	rec = conn.recv(20)		# receive some text from connected client
	rec = rec.strip()		# strip whitespace
	msg_type = 0

	logger.debug("received: " + rec + " END")

	# for now, only process minute ticks and perform a suitable action. in the future, also accept requests from button UI or website, to change mode or load JSON from file
	if not rec == "tick":
		conn.sendall("NAK")
		conn.close()
		continue	# go back to listening for incoming connections
	
	# minute tick was sent: check current time and compare with config, maybe switch mode
	# note: config currently hard coded, in the furure, a submodule should check against a .conf file

	t = time.localtime(time.time())

	if MODE == "abfahrten":
		if t.tm_hour == 19 and t.tm_min >= 0 and t.tm_min <= 30 and (t.tm_wday == 0 or t.tm_wday == 3):		# if service hour starts
			MODE = "sprechstunde"
		if t.tm_hour >= 23:					# if day ends
			MODE = "statisch"
	
	elif MODE == "statisch":
		if t.tm_hour >= 6 and t.tm_hour < 23:
			MODE = "abfahrten"					# if day starts


	elif MODE == "sprechstunde":
		if t.tm_hour >= 19 and t.tm_min >= 30:		# if service hour ends
			MODE = "abfahrten"
			
	logger.debug("Mode: " + MODE)

	if MODE == "statisch":
		continue				# stop here, if static mode is enabled


	# generate appropriate message
	# for abfahrten: get current departures from server, put into correct format
	# for the other two: only generate message if MODE_CHANGED, otherwise only send empty message

	content = []

	if MODE == "abfahrten":
				
		content = request_departures()
		
	elif MODE == "sprechstunde":
		content.append({"line":1, "align":"M", "text":"Herzlich Willkommen"})
		content.append({"line":2, "align":"M", "text":"zur"})
		content.append({"line":3, "align":"M", "text":"Internet-Sprechstunde!"})
		content.append({"line":4, "text":" "})
		content.append({"line":5, "text":" "})

	# generate a string that displays the current time
	time_string = str(t.tm_hour) + ":" + ("0" if t.tm_min < 10 else "") + str(t.tm_min)
	content.append({"line":5, "align": "R", "text": time_string})
		
	# connect to smartdifd
	try:
		out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)		# socket for outgoing connection to smartdfid
		out.connect(("localhost", 12581))
	except:
		logger.error("Failed to connect to smartdfid")
		conn.sendall("NAK")
		conn.close()
		continue
	
	# send data to smartdfid
	try:
		out.sendall(json.dumps(content))
		feedback = out.recv(20)
		feedback = feedback.strip()
		logger.debug("Feeback from smartdfid: " + feedback)
		out.close()
	except:
		logger.error("Failed to send data to smartdfid")
		out.close()
		conn.sendall("NAK")
		conn.close()
		continue
	
	# on success:
	conn.sendall("ACK")
	conn.close()

	
