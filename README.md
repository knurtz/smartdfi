# SmartDFI

This piece of software is able to control the LAFIS III board, which can be found in old departure monitors used in Dresden, Germany before the year 2017.

The software is based around several python daemons which are supposed to be launched at startup on a Raspberry Pi using initd. Sometime in the future the project will be updated to use systemd. The daemons communicate with each other by using sockets on the localhost of the Raspberry Pi.

## Hardware Overview

A wiring setup is following shortly.

## Software Overview

### smart\_dfi\_display

This python library provides a class called "Display". It is the lowest level of software and directly communicates with the LAFIS board via RS485 serial ports.
The class offers different methods to forge a so called _field telegram_ which can then be packaged and sent to the LAFIS board.

### smartdfid

This python daemon listens on port 12581 for JSON type data that follows a special format (will be documented in the Wiki section eventually). All data, that does not adhere to the format will be ignored. Valid JSON data will be converted in order to call methods from the Display class described above. Data will then be sent to the display.

### msggend

This python daemon listens on port 12583 for requests to generate a specific message. The created message is then sent to the smartdfid daemon which in turn sends it to the display using the Display class from smart\_dfi\_display. 
