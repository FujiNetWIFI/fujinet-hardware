# CoCo FujiNet Dragon Adapter

This adapter provides a replacement cable assembly for the CoCo FujiNet Rev0000, allowing it to connect to a Dragon 32/64 computer.

The cable assembly includes a PCB that provides a mounting platform for the 2×10 female IDC header that mates with the Dragon's Centronics connector.

To use this adapter, your Rev0000 board must have the EEPROM image dated June 15, 2026 (or later) and FujiNet firmware version 1.6.1 (or later). Earlier versions introduced significant timeout issues that prevented reliable operation.



![rev000](../../docs/Coco/rev000.jpg)

Schematic - [https://djtersteegc.github.io/fujinet-hardware/Coco/CoCo-FujiNet-Rev000-Schematic.pdf](https://github.com/FutureVision-Research/fujinet-hardware/blob/master/Coco/CoCo-FujiNet-Dragon-Adapter/CoCo-FujiNet-Dragon-Adapter-PCB-Schematic.pdf)

# PCB BOM

| Component                               | Qty  | Notes                              | Link                                                         |
| --------------------------------------- | ---- | ---------------------------------- | ------------------------------------------------------------ |
| 4P Right Angle XH2.54 JST Connector     | 1    |                                    | [AliExpress](https://www.aliexpress.us/item/2251832822174658.html) |
| IDC-20 (2x10) Female Header             | 1    |                                    | [AliExpress](https://www.aliexpress.us/item/2251832769816317.html) |

#PCB Assembly
1) Solder the JST connector with its opening facing the two holes labeled "Cable Tie."
2) Solder the IDC-20 connector to the edge of the PCB. Be sure to align the connector's key with the key marked on the top silkscreen.
Note: To hold the IDC-20 connector in place while soldering, insert a second IDC-20 connector on the opposite side of the PCB and clamp the assembly together with a vise.

# Cable Parts List

| Component                               | Qty  | Notes                              | Link                                                         |
| --------------------------------------- | ---- | ---------------------------------- | ------------------------------------------------------------ |
| 4P XH2.54 JST Recepticle                | 2    |                                    | [AliExpress](https://www.aliexpress.us/item/2251832815492773.html) |
| Four core 26AWG Shielded cable          | 36"  |(76cm)                              | [AliExpress](https://www.aliexpress.us/item/3256801872028158.html) |

# Cable Assembly



# Building the Serial Cable (Coco1/2/3)

If you have a later Coco2 or Coco3 with the serial port close to the cartridge port, you can buy some 300mm [prewired female connectors](https://www.aliexpress.us/item/2255801048702387.html) and [4mm nylon sleaving](https://www.aliexpress.us/item/2251832733475111.html) for cable making.  A Coco1 and early Coco2's with the serial port further from the cartridge port requires a longer 18" cable to reach. [Four core 26AWG UL2547 cable](https://www.aliexpress.us/item/3256801872028158.html) works well for this with some [XH2.54 4P connectors and terminals](https://www.aliexpress.us/item/2251832815492773.html). For either option you'll need a [DIN4 male](https://www.aliexpress.us/item/3256804124853512.html) plug for the serial port.

The DIN 4 serial cable pinout (looking at it from the backside of the connector) with the corresponding XH connector pins (they are also marked on the PCB).

![serial-cable-pinout](../docs/Coco/serial-cable-pinout.png)

And some completed cable pics:

![serial-cable-din4](../docs/Coco/serial-cable-din4.jpg)

![serial-cable-xh](../docs/Coco/serial-cable-xh.jpg)

# Building the Serial Cable (Dragon 32/64)

This was successfully tested by Brian Cox in July 2026. However, it is recommended that a shielded cable be used, with the drain wire connected to the ground pin on both connectors. Testing showed that using a non-shielded cable could prevent Config from launching in certain environments.

Info taken from https://web.archive.org/web/20140814201934/https://archive.worldofdragon.org/phpBB3/viewtopic.php?f=5&t=781

Normally you would need to invert the signals on the parallel port when connecting to a PC hosted DriveWire server, but the Fujinet takes care of that is software when selecting the Dragon HDB-DOS ROM so you can simply cable from the Fujinet over to the parallel port.

Here's the parallel port pinout looking at the port on the Dragon.

```
 19                  1
  . . . . . . . . . .
  . . . . . . . . . .
 20                  2

  1  Strobe      2  +5V
  3  Data 0      4  +5V
  5  Data 1      6  Ground
  7  Data 2      8  Ground
  9  Data 3     10  Ground
 11  Data 4     12  Ground
 13  Data 5     14  Ground
 15  Data 6     16  Ground
 17  Data 7     18  Ground
 19  !ACK       20  BUSY
```

And here's the wiring to the J1 serial port connector on the CocoFuji. Signal names are also silkscreened on the underside of the PCB.

![dragon-cable-wiring](../docs/Coco/dragon-cable-wiring.png)



