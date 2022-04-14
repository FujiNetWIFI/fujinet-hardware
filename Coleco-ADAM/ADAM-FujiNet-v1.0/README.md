# Coleco ADAM FujiNet v1.0

This is a public release of FujiNet hardware design for the Coleco ADAM Family Computer.

# License

This project is released under the CERN OHL v2.0.

# PCB

PCB's can be ordered by submitting the files from the _Gerbers_ directory to the fab house of your choice. The design was created using [Diptrace 3.3.1.3](https://diptrace.com). All components are through hole except for the MicroSD card socket.

# Bill of Materials (BOM)

A BOM file is provided with some specific parts numbers. Most parts are commonly available and can be substituted. The MicroSD sockets are readily available from AliExpress, Amazon, eBay and other places, sometimes called _Push Push TransFlash Socket_. Dimentional drawing is available in the _datasheets_ directory for reference.

# 3D Printed Case

STL files are provided in the _3D_ directory, created with Tinkercad:

[Coleco ADAM FujiNet v1.0 Case](https://www.tinkercad.com/things/jFMD73JR5Ap-coleco-adam-fujinet-v10-case)

# Assembly Notes

It is recommended to attach the MicroSD card socket first since it is the only SMD part and is more difficult to attach after the ESP32-DEVKITC headers are installed. 

Two 19 pin 2.54mm pitch female headers with 8.5mm height plastic are required for the ESP32-DEVKITC if using the 3D printed case. The case has a cutout for the MicroUSB socket at a height to match the headers. This allows the ESP32-DEVKITC to be removed from FujiNet if needed.

# Recommended Assembly Order

1. MicroSD Socket
2. Diodes & Single Resistors
3. Transistors
4. Power Switch
5. Resistor Array
6. Tactile Switches (Buttons)
7. Capacitor & RJ12 Jacks
8. ESP32-DEVKITC-VE with headers
9. LEDs (use the top case as a jig to hold them in place)

