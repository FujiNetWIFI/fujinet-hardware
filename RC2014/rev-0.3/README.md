# FujiNet - Designed for RC2014 - Rev 0.3

## Intro

This is the "Designed for RC2014" port of the FujiNet multi-function device.

Z80 Port used: 0x30

The address decoding circuit is copied from Spencer Owen's standard RC2014 modules.

This module uses a bit-banged SPI protocol to talk to the ESP32 DevKit. When the Z80 wants to send a command, it asserts BUS_CMD. The ESP32 acknowledges this by asserting the BUS_READY after initialising its SPI client driver. Then the SPI tranfers is done.

BUS_PROCEED is used for the Z80 to POLL when data is ready. This was intentional, rather than use interrupts, due to the simple fact that CP/M wan't really designed for handling interrupts through transient applications.

It is an early prototype, and very much Work In Progress (WIP) that is VERY likely to change in the near future.


## Caveats

There are MANY issues wrong with the Rev 0.3 design:

Z80 I/O Address decoding:
 - Due to a transposing error (I got A[3:5] wires the wrong way around), the actual Z80 I/O port address is 0x30
 - The other ports available from the 74HCT138 should be selectable as alternative addresses to better support other RC2014-like systems.

Power:
 - There is a feedback from the the ESP32 DevKit to the 5v rail to the RC2014 bus.

Interrupts:
 - Not used

Others:
 - BUS_DATA is currently unused


## TODO

Near term:
 - redesign the address decoder to better fit other RC2014-like systems. 0x30 WILL be the default address, though.
 - Refactor to use the Lolin D32 PRO with inbuilt uSD Card interface
 - Compliment BUS_PROCEED with interrupt line.
 - Possibly remove BUS_DATA

Long-term:
 - Possibly use a PCA9564 Parallel bus to I2C controller.
 - Possibly remove BUS_CMD as we only send commands



!!! USE AT YOUR OWN RISK !!!

Justin Skists (@jskists)

