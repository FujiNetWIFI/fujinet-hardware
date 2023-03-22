# FujiApple Rev00

This is a public release of FujiNet hardware design for the Apple II line of computers using the SmartPort interface. 

This design should be considered a development board and not a finished product. Setup information is available on the [Apple II FujiNet Quickstart Guide](https://github.com/FujiNetWIFI/fujinet-platformio/wiki/AppleII-FujiNet-Quickstart-Guide) page on the [wiki](https://github.com/FujiNetWIFI/fujinet-platformio/wiki/).

# SPI FIX Modification

This board shares the SPI MOSI pin between the SmartPort Bus and the SD Card. While this worked for floppy disk emulation, it was discovered later that CP/M emulation did not work. CP/M emulation needs constant access to the SD card due to it's filesystem being stored there which interferes with SmartPort bus access. The following hardware fix can be applied to the FujiApple Rev00 board to enable CP/M support. The firmware will automatically detect this fix and enable the CP/M device when accessed.


# License

This project is released under the CERN OHL v2.0.

# PCB

PCB's can be ordered by submitting the files from the _Gerbers_ directory to the fab house of your choice. The design was created using [Diptrace 3.3.1.3](https://diptrace.com). All components are through hole except for the MicroSD card socket and Tristate Buffer Gate.

# Bill of Materials (BOM)

A BOM file is provided with some specific parts numbers. Most parts are commonly available and can be substituted. The MicroSD sockets are readily available from AliExpress, Amazon, eBay and other places, sometimes called _Push Push TransFlash Socket_.

# Assembly Notes

It is recommended to attach the MicroSD card socket and Tristate Buffer first since they are the only SMD parts and is more difficult to attach after the ESP32-DEVKITC headers are installed. 

Two 19 pin 2.54mm pitch female headers are optional for the ESP32-DEVKITC-VE. Headers allow for the DEVKITC board to be removed and used for other projects or if a newer board revision becomes available.

# Recommended Assembly Order

1. MicroSD Socket & Tristate buffer
2. Diode & Single Resistors
3. C2 & C3 Capacitors
4. Buttons
5. LEDs
6. Debug & IDC20 Headers
7. Drive2 & Audio Headers
8. C1 Capacitor
9. ESP32-DEVKITC-VE with headers

