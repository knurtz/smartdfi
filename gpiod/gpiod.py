#!/usr/bin/env python
# -*- coding: utf-8 -*-
# make sure file is utf-8: ßöäü

import logging
import logging.handlers
import datetime
import socket
import RPi.GPIO

# =============== SETTINGS ==========================

LOG_FILENAME = "/home/display/smartdfi/gpiod/logfile.txt"
LOG_LEVEL = logging.INFO  			# Could be "INFO",  "DEBUG" or "WARNING"

HOST = "localhost"
PORT = 12582					# smartdfid: 12581, gpiod: 12582, msggend: 12583

# =============== FUNCTION DEFINITIONS ======================




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
sys.stdout = MyLogger(logger, logging.INFO)
sys.stderr = MyLogger(logger, logging.ERROR)

logger.info("Starting gpiod daemon.")


# =============== MAIN PROGRAM ==========================

# acquire GIPOs

# output for LEDs

# input for PIR sensor


# ============= CONFIGURE SOCKETS =================

inc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)         # socket for incoming connection from cron or user
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
        conn, addr = inc.accept()       # blocking call

        rec = conn.recv(20)             # receive some text from connected client
        rec = rec.strip()               # strip whitespace


