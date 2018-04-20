#!/usr/bin/env python


import smart_dfi_display
import time

disp = smart_dfi_display.Display()
for c in range (0x30, 0xf3, 15):
	disp.transmit_telegram(
        	disp.create_field_telegram([
                disp.create_field(1, str(hex(c)) + " " + chr(c) + " " + str(hex(c+1)) + " " + chr(c+1) + " " + str(hex(c+2)) + " " + chr(c+2)),
		disp.create_field(2, str(hex(c+3)) + " " + chr(c+3) + " " + str(hex(c+4)) + " " + chr(c+4) + " " + str(hex(c+5)) + " " + chr(c+5)),
		disp.create_field(3, str(hex(c+6)) + " " + chr(c+6) + " " + str(hex(c+7)) + " " + chr(c+7) + " " + str(hex(c+8)) + " " + chr(c+8)),
		disp.create_field(4, str(hex(c+9)) + " " + chr(c+9) + " " + str(hex(c+10)) + " " + chr(c+10) + " " + str(hex(c+11)) + " " + chr(c+11)),
		disp.create_field(5, str(hex(c+12)) + " " + chr(c+12) + " " + str(hex(c+13)) + " " + chr(c+13) + " " + str(hex(c+14)) + " " + chr(c+14))
		]))
	time.sleep(10)
