#!/usr/bin/env python
# -*- coding: utf-8 -*-


import smart_dfi_display       # needed for serial communication between computer and display controller (LAFIS)
disp = smart_dfi_display.Display()

disp.transmit_telegram(
disp.create_field_telegram([
	disp.create_field(1, "\xbd Herzlich Willkommen \xbe", align = "M"),

	disp.create_field(2, "\xbd in der WG 5/2! \xbe", align = "M"),
	
	disp.create_field(3, "Putzplan bis 26.11.:", font = "B"),
	
	disp.create_field(4, "Flo: Flur, Joh: Küche"),
		
	disp.create_field(5, "Luk: WC, Mit: Bad")
	
	]))


