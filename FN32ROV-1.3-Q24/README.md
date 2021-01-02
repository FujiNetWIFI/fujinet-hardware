# FujiNet FN32ROV-1.3-Q24

This is the second official public release of FujiNet hardware and is officially certified open source hardware by [OSHWA](https://oshwa.org). Certification details are available in the [certified directory](https://certification.oshwa.org/us000651.html) under the UID US000651.

![OSHWA Mark](https://github.com/FujiNetWIFI/fujinet-hardware/raw/master/images/oshwa-mark_us000651.png)

# Changes from 1.0
 * SIO lines connected to ESP32 through two 74LS07
 * P & N Channel transistors turn off 74LS07 when FujiNet is turned off separating the ESP32 from the Atari
 * Switch to QFN 24 CP20102 USB to UART Bridge
 * Hard reset button moved to SMD Snap Dome (optional)
 * Safe Reset button (handled in firmware) replaces Hard Reset button
 * New Power switch & 3D printed slide cover
 * Remove always on solder jumper
 * Add pull down for MOTOR for Cassette emulation
 * JTAG port removed. Signals available as test points

# PCB

PCB's for FN32ROV-1.3 can be ordered directly from the [OSH Park project page](https://oshpark.com/shared_projects/mkCMfFhV) or by submitting the files from the Gerbers directory to the fab house of your choice. The design was created using [Diptrace](https://diptrace.com).

SDM pads for passives are 0402 but you _can_ use 0603 sized passives on them.

# 3D Printed Cases

STL files are provided in this repo, originally created with Tinkercad:

* [FujiNet 400/800 Style Case Tinkercad Project](https://www.tinkercad.com/things/hrg5K91Tozb-fujinet-400-800-style-case-v13)
* [FujiNet XL Style Case Tinkercad Project](https://www.tinkercad.com/things/0JaDo39WziF-fujinet-xl-style-case-v13)
* [FujiNet XE Style Case Tinkercad Project](https://www.tinkercad.com/things/iSaAPU4abGV-fujinet-xe-style-case-v13)
