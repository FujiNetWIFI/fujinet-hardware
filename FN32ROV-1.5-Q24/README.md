# FujiNet FN32ROV-1.5-Q24

This is the third official public release of FujiNet hardware and is officially certified open source hardware by [OSHWA](https://oshwa.org). Certification details are available in the [certified directory](https://certification.oshwa.org/us000651.html) under the UID US000651.

![OSHWA Mark](https://github.com/FujiNetWIFI/fujinet-hardware/raw/master/images/oshwa-mark_us000651.png)

# Changes from 1.3

 * Add resistor divider on CP2102 VBUS
 * Add CP2102 capacitors
 * Connect CP2102 VIO to VDD
 * Add ESD (TVS) Protection Diodes for USB input
 * Change USB port footprint to use slots
 * Add 4.7k pull up resistor to SIO_DATAIN
 * Add 10k pull up resistors for uSD Card
 * Change auto-reset pull up resistors from 1k to 10k
 * Change SIO AUDIO_IN resistor to 10K

# PCB

PCB's for FN32ROV-1.5 can be ordered directly from the [OSH Park project page](https://oshpark.com/shared_projects/oz5VCXe2) or by submitting the files from the _Gerbers_ directory to the fab house of your choice. The design was created using [Diptrace 3.3.1.3](https://diptrace.com).

SMD pads for passives are 0402 but you _can_ use 0603 sized passives on them.

# 3D Printed Cases

STL files are provided in this repo, originally created with Tinkercad:

* [FujiNet 400/800 Style Case Tinkercad Project](https://www.tinkercad.com/things/hrg5K91Tozb-fujinet-400-800-style-case-v13)
* [FujiNet XL Style Case Tinkercad Project](https://www.tinkercad.com/things/0JaDo39WziF-fujinet-xl-style-case-v13)
* [FujiNet XE Style Case Tinkercad Project](https://www.tinkercad.com/things/iSaAPU4abGV-fujinet-xe-style-case-v13)
