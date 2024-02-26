# FujiApple Rev1.1 (FujiNet for Apple II & III)

This is a public release of FujiNet hardware design for the Apple II & III line of computers using the SmartPort interface. 

Minor changes from Rev1:
 * Right angle buttons for accessibility from top edge in vertical position
 * Replace Q1 with equivalent, more widely available and larger part

Usage and software information is available in the [Apple II FujiNet Quickstart Guide](https://github.com/FujiNetWIFI/fujinet-firmware/wiki/AppleII-%26-III-FujiNet-Quickstart-Guide) page on the [wiki](https://github.com/FujiNetWIFI/fujinet-platformio/wiki/).

![FujiApple Rev1 Complete Kit](FujiApple-Rev1-Kit.png)

# License

This project is released under the CERN OHL v2.0.

# PCB

PCBs can be ordered by submitting the files from the _Gerbers_ directory to the fab house of your choice. The design was created using [Diptrace 3.3.1.3](https://diptrace.com).

# Bill of Materials (BOM)

A BOM file is provided with some specific parts numbers. The MicroSD sockets are readily available from AliExpress, Amazon, eBay and other places, sometimes called _Push Push TransFlash Socket_.

# Assembly Notes

The 3D printable case was designed with [Tinkercad](https://www.tinkercad.com/things/0I7moiaIomw-fujiapple-rev11-case). Recommended filament color is Polymaker Matte PLA "Muted White" which is a close match to the Apple _Snow white_ color scheme.

A DB19 to IDC20 Female adapter is also available in this repository which is designed to connect directly to the FujiApple Rev1 or with a Female to Male cable. A 3D printable spacer is recommended when using the adapter directly with the Fujiapple. The FujiApple can also connect to a Disk II card with an IDC20 Female/Female cable.

There are two holes under the buttons on the front case for the LEDs. These holes are designed to be filled with 1.75mm clear filament which is used as a light pipe. Place the case face down on a flat surface. Insert the filament into the hole and cut it so a small amount is left above the surface on the inside. Use a soldering iron at around 250C to melt the filament until it's flush against the case. Demonstration available on [Youtube](https://youtu.be/darUmb1zTk4).

Two different 3D printable thumb screw caps are provided to make extra long screws for attaching the FujiApple directly to a IIc/+. The filenames denote what size screw to use in inches.

