# Apple II DB-19 to IDC-20 Female Adapter

This adapter was created to be used with FujiNet Rev1

<img src="https://github.com/FujiNetWIFI/fujinet-hardware/blob/master/AppleII/DB-19M-Adapter/images/DB19M_to_IDC20_Adapter.png" width="400px">

# License

This project is released under the CERN OHL v2.0.

# Bill of Materials (BOM)

 * IDC-20 Female Header
 * DB-19 Socket: 19pcs 5-745287-4

# Assembly Notes

Insert the 19 pins for the DB-19 socket into a DB-19 or DB-25 cable/adapter with the "fins" of the pins as shown below

<img src="https://github.com/FujiNetWIFI/fujinet-hardware/blob/master/AppleII/DB-19M-Adapter/images/DB19M_to_IDC20_Pin-Alignment.png" width="300px">
<img src="https://github.com/FujiNetWIFI/fujinet-hardware/blob/master/AppleII/DB-19M-Adapter/images/IMG_20221002_145542.jpg" width="300px">

The PCB is labeled "PIN SIDE" which is where the 3D printed connector goes. The unlabled side of the PCB is the solder side. Solder pin 1 and pin 19 first, ensuring the pins are straight/flush with the PCB then solder the remaining pins. Use side cutters to remove excess pins from the solder side.

Insert and solder the IDC-20 connector.

# 3D Printed DB-19 Connector

The connector should be printed with the PCB side down. Supports are not needed. The connector should fit snug on the pins with a little pressure.

The design was created with [Tinkercad](https://www.tinkercad.com/things/2HcX7NnmKWc-apple-ii-db-19-to-idc-20-adapter-nov2023)

# Usage

The +12V and -12V lines are not connected by default to prevent accidental damage. If you need these lines connected, add a solder blob to the labeled pads. 

The Drive 2 pin is connected by default through a solder pad. You can cut the trace between the pads to disable the Drive 2 Enable line and optionally add a solder blob to reconnect it.

