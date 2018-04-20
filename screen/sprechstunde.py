#!/usr/bin/env python
# -*- coding: utf-8 -*-


import smart_dfi_display       # needed for serial communication between computer and display controller (LAFIS)
disp = smart_dfi_display.Display()

disp.transmit_telegram(
disp.create_field_telegram([
	disp.create_field(1, "\xbd Herzlich Willkommen \xbe", align = "M"),

	disp.create_field(2, "zur", align = "M"),

	disp.create_field(3, "Internet-Sprechstunde", align = "M"),

	disp.create_field(4, " "), 

	disp.create_field(5, " ")

	]))


