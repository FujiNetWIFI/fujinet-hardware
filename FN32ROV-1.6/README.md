# FujiNet FN32ROV-1.6

This public release of FujiNet hardware and is officially certified open source hardware by [OSHWA](https://oshwa.org). Certification details are available in the [certified directory](https://certification.oshwa.org/us000651.html) under the UID US000651.

![OSHWA Mark](https://github.com/FujiNetWIFI/fujinet-hardware/raw/master/images/oshwa-mark_us000651.png)

# Changes from 1.5

Changes from v1.5:
 * Add SD Card Detect pin on GPIO 15
 * Change SIO 5V voltage divider for better accuracy
 * Run Motor Control signal through buffer
   * 10K pullup on ESP side Motor Control
   * 2K pulldown on Atari Side Motor Control
 * Increased hole size on PCB for new SIO Receptacle pins
 * Case Changes:
   * Increase screw hole size
   * New plug without holes
   * Tighter tolerance for SIO plug & added supports
   * Modified 3D Printed Receptacle for new pins
   * New external antenna case designs (requires U.FL/IPEX connector and correct resistor placement on ESP32 WROVER module)

# PCB

PCB's for FN32ROV-1.6 can be ordered by submitting the files from the _Gerbers_ directory to the fab house of your choice. The design was created using [Diptrace 3.3.1.3](https://diptrace.com).

SMD pads for passives are 0402 but you _can_ use 0603 sized passives on them.

# 3D Printed Cases

STL files are provided in this repo, originally created with Tinkercad:

* [FujiNet 400/800 Style Case Tinkercad Project](https://www.tinkercad.com/things/6fh1ie9V13I-fujinet-400-800-v16-case)
* [FujiNet 400/800 Antenna Case Tinkercad Project](https://www.tinkercad.com/things/4o1lzG0GDwn-fujinet-400-800-v16-antenna-case)
* [FujiNet XL Style Case Tinkercad Project](https://www.tinkercad.com/things/ctR4acVqKzW-fujinet-xl-v16-case)
* [FujiNet XL Antenna Tinkercad Project](https://www.tinkercad.com/things/4QhDuu80Pz3-fujinet-xl-v16-antenna-case)
* [FujiNet XE Style Case Tinkercad Project](https://www.tinkercad.com/things/2WxggbVZlMu-fujinet-xe-v16-case)
* [FujiNet XE Antenna Case Tinkercad Project](https://www.tinkercad.com/things/8ENljGqrKaO-fujinet-xe-v16-antenna-case)
