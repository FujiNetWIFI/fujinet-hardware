
# fujinet-devkit-shield

These files are sourced from https://github.com/djtersteegc/fujinet-devkit-shield

<img src="docs/combined-boards.jpg" alt="combined-boards" />

This is an alternative hardware platform for [FujiNet](https://fujinet.online/) that allows you to build your own using all through-hole technology (THT) components and an Espressif ESP32-DevKitC-VE devkit board.  You could probably also use a ESP32-DevKitC-VIE board, but you will need to either use an external IPEX connected antenna or engage in some micro soldering since the on-board PCB antenna is not connected by default. You must use ESP32-WROVER based devkit boards, the cheaper ESP32-WROOM boards lack the PSRAM needed by FujiNet code these days. 

The PCB is designed for flexibility in building, with different cabling options and headers for the buttons and LEDs if you want to mount this in your own enclosure. Most components are "jelly bean" parts you may already have or can be purchased for one or two cents in quantity from the usual China based suppliers.  Total cost of the build should be around $20, depending on where you source your parts.  Please see the assembly page for more details.

[Hardware Component Choices and Assembly](https://djtersteegc.github.io/fujinet-devkit-shield/assembly.html)

An interactive BOM and parts placement diagram is also available.

[Interactive Bill of Materials (BOM)](https://djtersteegc.github.io/fujinet-devkit-shield/ibom.html)

Currently this board is not supported by the FujiNet updater app so you will need to use Platform IO to build and upload your own binaries.  Build with the 8MB flash target since the devkit boards have half the flash of the 16MB WROVER modules used on the SIO mounted FujiNet designed by [mozzwald](https://github.com/mozzwald).  In normal operation is should not really matter since 6MB in the 16MB version is currently reserved for over the air (OTA) updates and the release build uses a little more than 2MB of flash as of March 2021 so lots of free space still for future development.

[Board bring up for FujiNet Platform.IO code](https://github.com/FujiNetWIFI/fujinet-platformio/wiki/Board-bring-up-for-FujiNet-Platform.IO-code)

STL's and the [DesignSpark Mechanical](https://www.rs-online.com/designspark/mechanical-software) source file for a 3D printable enclosure are in the **enclosure** directory. Assemble with four M3x10mm screws. Make sure to print 3 copies of the button file.

<img src="docs/designspark.jpg" alt="designspark" />



<img src="docs/enclosure.jpg" alt="enclosure" />

# Getting a Board

If I have extra PCB's, they will be listed on Tindie.

[https://www.tindie.com/products/tersteeg/fujinet-devkit-shield/](https://www.tindie.com/products/tersteeg/fujinet-devkit-shield/)

Otherwise you can download the Gerbers and use your favorite fab (JLCPCB, PCBWay, etc.) to make your own batch.  It's a standard two layer, 1oz copper board with dimensions of 99mm x 56mm so it squeaks under the 100mm x 100mm limit of the cheap Chinese fabs.

# Hardware Revisions

### Version 1.0

Mostly tested. Standard pin header cable with the SMD MicroSD card connector works.  Still waiting for DB15 connectors to test that cable configuration and a 4.7uf ceramic cap for audio in line. Will also build that one with the micro SD breakout board to verify.  External pin headers for the buttons and LEDs are also untested, but should work. Equivalent to version 1.3+ (pull-up resistors on the SIO and SD card lines) of the SIO port mounted FujiNet.
