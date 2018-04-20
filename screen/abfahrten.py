#!/usr/bin/env python
# -*- coding: utf-8 -*-

import smart_dfi_display       # needed for serial communication between computer and display controller (LAFIS)
disp = smart_dfi_display.Display()

disp.transmit_telegram(
disp.create_field_telegram([
	disp.create_field(1, "66  Mockritz"),
	disp.create_field(1, "2", align = "R"),

	disp.create_field(2, "3   Wilder Mann"),
	disp.create_field(2, "5", align = "R"),

	disp.create_field(3, "8   Südvorstadt"),
	disp.create_field(3, "10", align = "R"),

	disp.create_field(4, "66  Hauptbahnhof"),
	disp.create_field(4, "13", align = "R"),


	disp.create_field(5, "Reichenbachstraße", align = "M", font = "B")

	]))


