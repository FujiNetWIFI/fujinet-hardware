# CoCo FujiNet Dragon Adapter

This adapter provides a replacement PCB and cable for the CoCo FujiNet Rev0000 which allows connection to a Dragon 32/64 computer.

In order to take advantage of this cable, your Rev0000 board must have the EEPROM file updated on June 15, 2026 (or later) and FujiNet firmware 1.6.1 (or later). Previous versions of both these files introduced significant timeout problems.



![rev000](../docs/Coco/rev000.jpg)

Schematic - https://djtersteegc.github.io/fujinet-hardware/Coco/CoCo-FujiNet-Rev000-Schematic.pdf

# BOM


| Component                               | Qty  | Notes                              | Link                                                         |
| --------------------------------------- | ---- | ---------------------------------- | ------------------------------------------------------------ |
| 100nF 50V Ceramic Capacitor             | 1    | 5mm Lead Spacing                   | [AliExpresss](https://www.aliexpress.us/item/3256805505361280.html) |
| 47uF 10V 3528 Tantalum Capacitor        | 1    | B Type Case (or smaller)           | [AliExpress](https://www.aliexpress.us/item/3256805505328370.html) |
| 100uF 10V Electrolytic Capacitor        | 1    | 6.3mm Diameter, 2.5mm Lead Spacing | [AliExpress](https://www.aliexpress.us/item/3256805505601375.html) |
| 10K 1/4w Resistor                       | 2    |                                    | [AliExpress](https://www.aliexpress.us/item/3256805483572082.html) |
| 1K 1/4w Resistor                        | 4    |                                    | [AliExpress](https://www.aliexpress.us/item/3256805483572082.html) |
| 10K 9 Pin Resistor Array                | 1    |                                    | [AliExpress](https://www.aliexpress.us/item/3256805495673085.html) |
| 1N5817 Diode                            | 1    |                                    | [AliExpress](https://www.aliexpress.us/item/3256805521351480.html) |
| 5mm LED (White)                         | 1    | Wifi                               | [AliExpress](https://www.aliexpress.us/item/3256805522045262.html) |
| 5mm LED (Orange)                        | 1    | Activity                           | [AliExpress](https://www.aliexpress.us/item/3256805522045262.html) |
| 27C512 Compatible EPROM or EEPROM       | 1    | Winbond W27C512 EEPROM             | [AliExpress](https://www.aliexpress.us/item/3256806559813313.html) |
| 28 Pin Wide DIP Socket                  | 1    |                                    | [AliExpress](https://www.aliexpress.us/item/3256805562135776.html) |
| 6mm x 6mm x 8mm Right Angle Tact Swtich | 2    |                                    | [AliExpress](https://www.aliexpress.us/item/2255800678062916.html) |
| 2 Way DIP Slide Switch                  | 1    |                                    | [AliExpress](https://www.aliexpress.us/item/3256801301494043.html) |
| microSD Socket                          | 1    | Push-Push TransFlash               | [AliExpress](https://www.aliexpress.us/item/3256801145064294.html) |
| 4P Right Angle XH2.54 Connector         | 1    | See below for other cable parts.   | [AliExpress](https://www.aliexpress.us/item/2251832822174658.html) |
| ESP32-DevkitC-VIE                       | 1    | ESP32-DevkitC-VE Also Works        | [Amazon](https://www.amazon.com/dp/B087TF2L27)               |



# Assembly

Unlike the previous revisions, you will need to solder the ESP32 onto the PCB since the cartridge format is to short to allow it to be mounted on standard 8.5mm tall female headers. Print four of the [4mm spacers](CoCo-FujiNet-Rev0000/3D/STL/CoCo-FujiNet-Rev000-4mm-Spacer.stl) to mount the ESP32 elevated from the PCB to help improve the wifi performance if using the VE version with integrated antenna and provide more space between the SD slot and USB port.

![rev000-spacers](../docs/Coco/rev000-spacers.jpg)

![rev000-ports](../docs/Coco/rev000-ports.jpg)

The DIP switch allows for up to four 16K ROM images to loaded and selected on a 27c512 (or equivalent) EPROM. There is a precompiled image in the [ROM directory](ROM) with HDB-DOS DriveWire 3 images for the various Coco's and Tano Dragon's from the hdbdos-snapshot20190324 archive.

| Computer     | ROM           | Baud    | SW1-1 (A14) | SW1-2 (A15) |
| ------------ | ------------- | ------- | ----------- | ----------- |
| Coco 1       | hdbdw3cc1.rom | 38,400  | ON          | ON          |
| Coco 2       | hdbdw3cc2.rom | 57,600  | OFF         | ON          |
| Coco 3       | hdbdw3cc3.rom | 115,200 | ON          | OFF         |
| Dragon 32/64 | hdbdw3dgn.rom | 57,600  | OFF         | OFF         |

The case is designed to be printed at a 0.2mm layer height.  Secure the PCB and two case halves with four M3x10mm to 20mm screws in the center four holes, and optionally four M3x16mm to 20mm screws in the outer four holes.  Overkill, but results in a very solid feeling cartridge with minimal gaps between the two halves.  There are two zip tie mounts for the serial cable and VIE external antenna.

![rev000-bottom](../docs/Coco/rev000-bottom.jpg)

![rev000-assembled](../docs/Coco/rev000-assembled.jpg)

![rev000-working](../docs/Coco/rev000-working.jpg)



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



# Flashing Your FujiNet

Tandy CoCo builds are available in the [Fujinet Flasher](https://fujinet.online/download/).

# Usage

Insert into cart slot and plug attached cable into your Coco's serial port.

Assuming the FujiNet device is correctly flashed, it should launch into the Fujinet config app on power up.

![fujinet-loading](../docs/Coco/fujinet-loading.jpg)

