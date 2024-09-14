# Apple II DB-19 to IDC-20 Female Adapter (v2)

This adapter was created to be used with FujiNet Rev1

# License

This project is released under the CERN OHL v2.0.

# Bill of Materials (BOM)

 * IDC-20 (2x10) Female Header: [Aliexpress](https://www.aliexpress.us/item/2251832769816317.html)
 * DB-19 Pins 19pcs: [Aliexpress](https://www.aliexpress.us/item/3256801088745958.html)
 * M3 x 5mm Self Tapping Wood Screws 2pcs: [Aliexpress](https://www.aliexpress.us/item/3256803466380721.html)

 * Optional IDC20 Female to IDC20 Male cable: [Aliexpress](https://www.aliexpress.us/item/2251832764588330.html)

# Assembly Notes

Solder the IDC20 female socket onto the PCB in the proper orientation noted on the PCB silk screen. Print the DB-19 hood. Place the 3D printed hood onto a DB-19 female connector and insert 19 male pins. Place the PCB over the pins and solder them. Screw the PCB to the hood with two M3 x 5mm wood screws.

# 3D Printed DB-19 Connector

The connector should be printed with the PCB side down. Supports are not needed. The spacer is recommended when using the adapter plugged directly into a Rev1 FujiNet for Apple II.

The design was created with [Tinkercad](https://www.tinkercad.com/things/6q5F7LSWcoJ-fujinet-apple-ii-db-19-adapter-female-v2)

# Usage

The +12V and -12V lines are not connected by default to prevent accidental damage. If you need these lines connected, add a solder blob to the labeled pads. 

The Drive 2 pin is connected by default through a solder pad. You can cut the trace between the pads to disable the Drive 2 Enable line and optionally add a solder blob to reconnect it.

