# Rev0

Needs to be reworked to connect the CD pin of the serial port to IO22 on the ESP32.  Bend up the forth pin on a 4 pin XH2.54 connector, solder some wire to it, insert the remaining three pins in J1 (Serial Port), and solder the 4th pin with the bodge wire to IO22 on the ESP32.

![rev0-rework-top](../../../docs/Coco/rev0-rework-top.jpg)

![rev0-rework-bottom](../../../docs/Coco/rev0-rework-bottom.jpg)

You also need to cut the trace between the output of the low pass filter and the input to the LM386 pot in order to install a small capacitor to remove the DC offset.  It's on the underside of the PCB between pin one of R12 and pin two of R17.  Any small electrolytic cap around 10uF should work.

![rev0-dc-offset-cut](../../../docs/Coco/rev0-dc-offset-cut.jpg)

![rev0-dc-offset-cap](../../../docs/Coco/rev0-dc-offset-cap.jpg)

KiCad PCB Layout - https://djtersteegc.github.io/fujinet-hardware/Coco/pcb-traces-rev0.png

BOM and build is the same as Rev00 to see below for more info.

# Rev00

Connected the CD pin of the serial port to IO22.  You will still need to install the capacitor on the back if attempting to build the cassette portion of the board.

Schematic - https://djtersteegc.github.io/fujinet-hardware/Coco/CoCo-FujiNet-Rev00-Schematic.pdf

Interactive BOM - https://djtersteegc.github.io/fujinet-hardware/Coco/ibom-Rev00.html

![rev00-top.png](../../../docs/Coco/rev00-top.png)

![rev00-side.png](../../../docs/Coco/rev00-side.png)

You'll need 8.5mm high [2.54mm female header strips](https://www.aliexpress.us/item/2251832416528370.html) to mount the ESP32.  Buy the 1x40 versions and cut to length.

MicroSD socket footprint is the common [Chinese push-push version](https://www.aliexpress.us/item/2251832613969983.html) used on all the FujiNet's to date.

You can either assemble the LM386 based amp circuit, or use one of these [premade modules](https://www.aliexpress.us/item/3256805809816872.html) on the board instead. If using the module all the components in the outline area can be excluded, as well as C2 and C7.

The cable sockets on the board are the cheap [XH2.54 4p angle](https://www.aliexpress.us/item/2251832735749189.html) connectors.   Buy some [prewired female connectors](https://www.aliexpress.us/item/2255801048702387.html) and [4mm nylon sleaving](https://www.aliexpress.us/item/2251832733475111.html) for cable making.  You'll need a [DIN4 male](https://www.aliexpress.us/item/3256804124853512.html) plug for the serial port, and [DIN5 male](https://www.aliexpress.us/item/3256804124853512.html) plug for the cassette port.

# Building a "Minimal" Rev0/00

If you already have a CocoSDC or some other way to load HDB-DOS with DriveWire 3 support, you can skip building the cassette  portion of the board.

Here's what a minimal build looks like.  You'll only need R9, R11, R13, RN1, D1, D3, two 6mm tact switches, the MicroSD card socket, some female headers for the ESP, and one XH2.54 4p connector.

![rev0-minimal](../../../docs/Coco/rev0-minimal.jpg)

![rev0-minimal-complete](../../../docs/Coco/rev0-minimal-complete.jpg)

## Flashing HDB-DOS on your CocoSDC

Grab SDCFLASH from the [Color Computer Archive](https://colorcomputerarchive.com/search?q=SDCFLASH). It contains a number of different HDB-DOS images for the various Coco models.

`HDBDW3C1.ROM - HDB-DOS for Drivewire 3 (Coco 1) (Cloud-9)
HDBDW3C2.ROM - HDB-DOS for Drivewire 3 (Coco 2) (Cloud-9)
HDBDW3C3.ROM - HDB-DOS for Drivewire 3 (Coco 3) (Cloud-9)`

Since I'm using a Coco2, I used **HDBDW3C2.ROM** and flashed it to the slot number 3 on my CocoSDC.  Set your DIP jumpers accordingly to use this new ROM image instead of the standard SDC-DOS image in slot 0. See the CocoSDC docs for more details.

# Rework to Set Baud Rate

With the introduction of Rev000 and dip switch selectable HDB-DOS firmware images, the Fujinet code now by default detects the status of the ROM image selected on ESP32 pins 3 and 4.  Since these pins are input only and don't have any pull-up/pull-down options in code, without any rework they are both read as low and the firmware selects 38,400 which is correct for the Coco1 DW3 ROM image.  If you want to select 57,600 or 115,200 baud for either a Coco2 or Coco3 ROM image, you can either solder 10K pull-up resistors between the appropiate pins and pin 1 of the ESP32 (3.3V), or use **FORCE_UART_BAUD** in https://github.com/FujiNetWIFI/fujinet-firmware/blob/master/lib/bus/drivewire/drivewire.cpp to ignore this pins and force the baud rate based on whatever you hardcode in the the firmware.

Below pin3  is pulled high, and pin 4 left low which reads as a Coco2 and sets the baud rate to 57,600.

![rev00-baud-rework](E:/Vintage Computers/FujiNet/fujinet-hardware/docs/Coco/rev00-baud-rework.jpg)

# Building the Serial Cable

The DIN 4 serial cable pinout (looking at it from the backside of the connector) with the corresponding XH connector pins (they are also marked on the PCB).

![serial-cable-pinout](../../../docs/Coco/serial-cable-pinout.png)

And some completed cable pics:

![serial-cable-din4](../../../docs/Coco/serial-cable-din4.jpg)

![serial-cable-xh](../../../docs/Coco/serial-cable-xh.jpg)

# Flashing Your FujiNet

At this stage there is no official release of the Coco firmware in the [Fujinet Flasher](https://fujinet.online/download/).  But you can still use it to easily flash a precompile version (check the Discord), or you can [compile one yourself](https://github.com/FujiNetWIFI/fujinet-firmware/wiki/Board-Bring-Up-Software).

# Usage

Rev0 and Rev00 - Plug serial cable into your Coco's serial port. Supply power to the Fujinet via the USB port on the ESP32. Plug CocoSDC or other ROM cart into cart slot to bootstrap HDB-DOS.

Assuming the FujiNet device (and CocoSDC if needed) is correctly flashed, it should launch into the Fujinet config app on power up.

![fujinet-loading](../../../docs/Coco/fujinet-loading.jpg)

