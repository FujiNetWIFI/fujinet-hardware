# FujiNet FN32ROV-1.3-Q24

This is the second official public release of FujiNet hardware and is officially certified open source hardware by [OSHWA](https://oshwa.org). Certification details are available in the [certified directory](https://certification.oshwa.org/us000651.html) under the UID US000651.

![OSHWA Mark](https://github.com/FujiNetWIFI/fujinet-hardware/raw/master/images/oshwa-mark_us000651.png)

# IMPORTANT BUGFIXES

It is not recommended to make these boards. A new version will replace this board. The original release of v1.3 had errors that could cause a failure to flash the esp32 from some computers while working fine from others. This was due to several reasons:

 1. CP2102 VIO pin was left unconnected
 2. Weak R6 & R7 pullups
 3. Improper decoupling capacitors for CP2102

Boards made with the error can be fixed by replacing R6 & R7 with 10K resistors, creating a solder bridge from pin 5 to pin 6 on U2, adding a 4.7uF cap to C5, replace C6 with a 0.1uF cap and adding 4.7uF cap to C6. See [CP2102 Bodge Image](https://github.com/FujiNetWIFI/fujinet-hardware/blob/master/FN32ROV-1.3-Q24/CP210x_RESET-BUG_FIX_FINAL.jpg)

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

SMD pads for passives are 0402 but you _can_ use 0603 sized passives on them.

# 3D Printed Cases

STL files are provided in this repo, originally created with Tinkercad:

* [FujiNet 400/800 Style Case Tinkercad Project](https://www.tinkercad.com/things/hrg5K91Tozb-fujinet-400-800-style-case-v13)
* [FujiNet XL Style Case Tinkercad Project](https://www.tinkercad.com/things/0JaDo39WziF-fujinet-xl-style-case-v13)
* [FujiNet XE Style Case Tinkercad Project](https://www.tinkercad.com/things/iSaAPU4abGV-fujinet-xe-style-case-v13)
