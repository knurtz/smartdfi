#!/usr/bin/env python
# -*- coding: utf-8 -*-
# make sure file is utf-8: ßöäü

import logging
import logging.handlers
import datetime
import time			# for sleep
import socket
import RPi.GPIO as g

# =============== SETTINGS ==========================

LOG_FILENAME = "/home/display/smartdfi/gpiod/logfile.txt"
LOG_LEVEL = logging.DEBUG  			# Could be "INFO",  "DEBUG" or "WARNING"

HOST = "localhost"
PORT = 12582					# smartdfid: 12581, gpiod: 12582, msggend: 12583

PIR_TIMER = 0
MOTION_TIMEOUT = 3				# timeout in minutes

LED1_PIN = 16
LED2_PIN = 18
LED3_PIN = 22

PIR_PIN = 7

CLK1_PIN = 11
CLK2_PIN = 13
CLKEN_PIN = 15

CLK_DEFAULT_STATE = True
CLK_ENABLE_STATE = True

# =============== FUNCTION DEFINITIONS ======================

def setup_gpio():

	# set up RPi.GPIO
	g.setmode(g.BOARD)
	
	# outputs for LEDs
	g.setup(LED1_PIN, g.OUT)
	g.setup(LED2_PIN, g.OUT)
	g.setup(LED3_PIN, g.OUT)
	
	# outputs for clock
	g.setup(CLK1_PIN, g.OUT)
	g.setup(CLK2_PIN, g.OUT)
	g.setup(CLKEN_PIN, g.OUT)

	# default values for outputs
	leds_off()
	g.output(CLKEN_PIN, not CLK_ENABLE_STATE)
	g.output(CLK1_PIN, CLK_DEFAULT_STATE)
	g.output(CLK2_PIN, CLK_DEFAULT_STATE)

	# interrupt input for PIR sensor
	g.setup(7, g.IN, pull_up_down = g.PUD_DOWN)
	g.add_event_detect(7, g.RISING, callback = pir_callback)
	

def leds_on():
	g.output(LED1_PIN, True)
	time.sleep(0.1)
	g.output(LED2_PIN, True)
	time.sleep(0.1)
	g.output(LED3_PIN, True)

def leds_off():
	g.output(LED1_PIN, False)
	g.output(LED2_PIN, False)
	g.output(LED3_PIN, False)


def minute_callback():
	global PIR_TIMER

	if PIR_TIMER > 0:
		PIR_TIMER = PIR_TIMER - 1
		if PIR_TIMER == 0:
			logger.debug("Motion timeout reached")
			leds_off()	


def pir_callback(channel):
	global PIR_TIMER

	if channel == 7:
		# reset timer to 5 minutes
		PIR_TIMER = MOTION_TIMEOUT
		logger.debug("Motion detected")
		leds_on()

		


# =============== CONFIGURE LOGGING ==========================

# configure logger
logger = logging.getLogger("gpiod_logger")
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
#sys.stdout = MyLogger(logger, logging.INFO)
#sys.stderr = MyLogger(logger, logging.ERROR)

logger.info("Starting gpiod daemon.")


# =============== MAIN PROGRAM ==========================

try:
	if __name__ == "__main__":
		
		setup_gpio()
		
		# create listening socket
		inc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)         # socket for incoming connection from cron or user
		inc.settimeout(None)
		inc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		logger.debug("Incoming Socket created")
	
	        inc.bind((HOST,PORT))
		inc.listen(0)
		logger.info("Now listening on port " + str(PORT))

		while(True):
		        conn, addr = inc.accept()       	# blocking call
			rec = conn.recv(20).strip()             # receive some text from connected client, strip whitespace
				
			if rec == "tick":
				minute_callback()
				conn.sendall("ACK")
				conn.close()
				continue	# go back to listening for incoming connections

			else:
				conn.sendall("NAK")
				conn.close()
				continue	# go back to listening for incoming connections


except KeyboardInterrupt:
	print "Keyboard Interrupt, exiting"

except socket.error, msg:
        logger.error("Bind failed. Error Code: " + str(msg[0]) + " - Error Message: " + msg[1])
 
finally:
	g.cleanup()



