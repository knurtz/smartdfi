#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import logging.handlers
import sys
import datetime
import socket
import re				# regular expressions
import json
import requests			# simple http requests
import ConfigParser		# for .cfg files

# =============== SETTINGS ==========================

LOG_FILENAME = "/home/display/smartdfi/msggend/logfile.txt"
LOG_LEVEL = logging.DEBUG 			# Could be "INFO",  "DEBUG" or "WARNING"

HOST = "localhost"
PORT = 12583						# smartdfid: 12581, gpiod: 12582, msggend: 12583


# =============== FUNCTION DEFINITIONS ======================

def read_config():
	parser = ConfigParser.ConfigParser()
	config = default_config()

	# try reading the config file
	try:
		parser.read("config.cfg")
	except:
		return config

	# retrieve info about all sections
	sections = []
	for s in parser.sections():

		# retrieve general information
		if s == "General":
			# retrieve all general information, currently only "TimePosition"
			for k in parser.options(s):
				config[k] = parser.get(s, k)
			continue

		# ignore all sections, that do not match the (h)h:mm pattern
		if not re.match(r'^[0-9]?[0-9]:[0-9][0-9]$', s):
			logger.error("Parsing config. Ignoring section " + s)
			continue

		# this should always work because of the regex check before, but making sure...
		try:
			hours = int(s[:s.find(":")])
			minutes = int(s[s.find(":")+1:])
		except:
			logger.error("Parsing config. Error in section " + s)
			continue

		section = {"starthour": hours, "startminute": minutes}
		# copy config for each valid section
		for k in parser.options(s):
			section[k] = parser.get(s, k)

		if "mode" in section:
			sections.append(section)

		else:
			logger.error("Parsing config. No mode given for section " + s)

	# if configuration contains at least one valid section, replace default section and return
	if len(sections) > 0:
		config["sections"] = sections

	return config


def default_config():
	return {"timeposition": "BottomRight", "sections": [{"starthour": 0, "startminute": 0, "mode": "Text", "text": "Fehlerhafte Konfiguration"}]}


def update_section(sections):

	cur = -1
	now = datetime.datetime.now()

	# go through sections and check if starttime and weekday criteria, update current section accordingly
	for i in range(0, len(sections)):
		if isAfter(now.hour, now.minute, sections[i]["starthour"], sections[i]["startminute"]):
			# skip sections that do not apply to the current day
			if "weekdays" in sections[i]:
				if sections[i]["weekdays"].find(str(now.weekday())) == -1:
					continue
			cur = i
		else:
			break

	return cur


def isAfter(hour1, minute1, hour2, minute2):

	if hour1 > hour2 or (hour1 == hour2 and minute1 > minute2):
		return True
	else:
		return False


def request_departures(stopid, stopname, lines):
	array = []
	payload = {"stopid": stopid, "limit": 15}

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
			line_name = d["LineName"]  # this contains the line number as a string, do not confuse with dfi line, which refers to text rows
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

		if dfi_line > (lines - 1):
			break

	array.append({"line":lines, "align":"L", "text":stopname})
	return array



# =============== MAIN PROGRAM ==========================

try:
	if __name__ == "__main__":

		# Make a handler that writes to a file, making a new file at midnight and keeping 3 backups
		handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when = "midnight", backupCount = 3)

		# Format each log message like this
		formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')

		# configure logger
		logger = logging.getLogger("msggend_logger")
		logger.setLevel(LOG_LEVEL)
		handler.setFormatter(formatter)
		logger.addHandler(handler)

		# Make a class we can use to capture stdout and sterr in the log
		class MyLogger(object):
		        def __init__(self, logger, level):
		                #Needs a logger and a logger level.
		                self.logger = logger
		                self.level = level

		        def write(self, message):
		                # Only log if there is a message (not just a new line)
		                if message.rstrip() != "":
		                        self.logger.log(self.level, message.rstrip())

		# Replace stdout and stderr with logging to file at DEBUG/ERROR level
		#sys.stdout = MyLogger(logger, logging.DEBUG)
		#sys.stderr = MyLogger(logger, logging.ERROR)

		logger.info("Starting msggend daemon.")

		# read configuration
		config = read_config()
		print config

		# start off being in section -1 (no section found)
		current_section = -1

		# create socket for incoming connection from cron or user
		inc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		inc.settimeout(None)
		inc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

		logger.debug("Incoming Socket created")

		inc.bind((HOST,PORT))
		inc.listen(0)

		logger.debug("Now listening")

		while(True):
			conn, addr = inc.accept()	# blocking call

			rec = conn.recv(20)		# receive some text from connected client
			rec = rec.strip()		# strip whitespace

			logger.debug("received: " + rec + " END")

			# for now, only process minute ticks and perform a suitable action. in the future, also accept requests from button UI or website, to change mode or load JSON from file
			if not rec == "tick":
				conn.sendall("NAK")
				conn.close()
				continue	# go back to listening for incoming connections

			# minute tick was sent: check current time and compare with config, maybe switch mode

			current_section = update_section(config["sections"])

			print ("Current section updated to " + str(current_section))

			# do nothing if no config for the current time was found
			if current_section == -1:
				conn.sendall("ACK")
				conn.close()
				continue

			sec = config["sections"][current_section]

			if sec["mode"] == "Off":
				conn.sendall("ACK")
				conn.close()
				continue

			if sec["mode"] == "Text":
				content.append({"line":1, "text": sec["text"]})

			elif sec["mode"] == "Json":
				with open("json/" + sec["filename"]) as json_data:
					content = json.load(json_data)

			elif sec["mode"] == "Stop":
				content = request_departures(sec["stopid"], sec["stopname"], int(config["lines"]))

			# generate a string that displays the current time (hard coded for now)
			t = datetime.datetime.now()
			time_string = str(t.hour) + ":" + ("0" if t.minute < 10 else "") + str(t.minute)
			content.append({"line":int(config["lines"]), "align": "R", "text": time_string})

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
				logger.debug("Feedback from smartdfid: " + feedback)
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

except KeyboardInterrupt:
	print "Keyboard Interrupt, exiting"

except socket.error, msg:
	logger.error("Bind failed. Error Code: " + str(msg[0]) + " - Error Message: " + msg[1])
	sys.exit()
