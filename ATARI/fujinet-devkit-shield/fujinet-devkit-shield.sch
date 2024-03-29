EESchema Schematic File Version 4
EELAYER 30 0
EELAYER END
$Descr A4 11693 8268
encoding utf-8
Sheet 1 1
Title "FujiNet ESP32-DevKitC-VE Shield"
Date "2021-02-13"
Rev "1.0"
Comp ""
Comment1 "**UNTESTED**"
Comment2 ""
Comment3 ""
Comment4 ""
$EndDescr
$Comp
L ESP32-DEVKITC-32U:ESP32-DEVKITC-32U U1
U 1 1 602420D6
P 6750 2400
F 0 "U1" H 6750 3567 50  0000 C CNN
F 1 "ESP32-DEVKITC-VE" H 6750 3476 50  0000 C CNN
F 2 "ESP32-DEVKITC-32U:MODULE_ESP32-DEVKITC-32U" H 6750 2400 50  0001 L BNN
F 3 "" H 6750 2400 50  0001 L BNN
F 4 "Manufacturer Recommendations" H 6750 2400 50  0001 L BNN "STANDARD"
F 5 "N/A" H 6750 2400 50  0001 L BNN "PARTREV"
F 6 "ESPRESSIF" H 6750 2400 50  0001 L BNN "MANUFACTURER"
	1    6750 2400
	1    0    0    -1  
$EndComp
$Comp
L 74xx:SN74LS07N U3
U 1 1 602443A7
P 2550 1150
F 0 "U3" H 2550 1467 50  0000 C CNN
F 1 "SN74LS07N" H 2550 1376 50  0000 C CNN
F 2 "Package_DIP:DIP-14_W7.62mm_Socket_LongPads" H 2550 1150 50  0001 C CNN
F 3 "www.ti.com/lit/ds/symlink/sn74ls07.pdf" H 2550 1150 50  0001 C CNN
	1    2550 1150
	1    0    0    -1  
$EndComp
$Comp
L 74xx:SN74LS07N U4
U 1 1 60244E57
P 4200 1150
F 0 "U4" H 4200 1467 50  0000 C CNN
F 1 "SN74LS07N" H 4200 1376 50  0000 C CNN
F 2 "Package_DIP:DIP-14_W7.62mm_Socket_LongPads" H 4200 1150 50  0001 C CNN
F 3 "www.ti.com/lit/ds/symlink/sn74ls07.pdf" H 4200 1150 50  0001 C CNN
	1    4200 1150
	1    0    0    -1  
$EndComp
$Comp
L Device:LED D1
U 1 1 6024CCC1
P 4050 5550
F 0 "D1" H 4043 5767 50  0000 C CNN
F 1 "WIFI" H 4043 5676 50  0000 C CNN
F 2 "LED_THT:LED_D5.0mm" H 4050 5550 50  0001 C CNN
F 3 "~" H 4050 5550 50  0001 C CNN
	1    4050 5550
	1    0    0    -1  
$EndComp
$Comp
L Device:LED D2
U 1 1 60250842
P 4050 6250
F 0 "D2" H 4043 6467 50  0000 C CNN
F 1 "SIO" H 4043 6376 50  0000 C CNN
F 2 "LED_THT:LED_D5.0mm" H 4050 6250 50  0001 C CNN
F 3 "~" H 4050 6250 50  0001 C CNN
	1    4050 6250
	1    0    0    -1  
$EndComp
$Comp
L Device:LED D3
U 1 1 60250B99
P 4050 6950
F 0 "D3" H 4043 7167 50  0000 C CNN
F 1 "BLUETOOTH" H 4043 7076 50  0000 C CNN
F 2 "LED_THT:LED_D5.0mm" H 4050 6950 50  0001 C CNN
F 3 "~" H 4050 6950 50  0001 C CNN
	1    4050 6950
	1    0    0    -1  
$EndComp
$Comp
L Device:R R1
U 1 1 60250FDF
P 3500 5550
F 0 "R1" V 3293 5550 50  0000 C CNN
F 1 "1K" V 3384 5550 50  0000 C CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal" V 3430 5550 50  0001 C CNN
F 3 "~" H 3500 5550 50  0001 C CNN
F 4 "For WiFi LED" V 3500 5550 50  0001 C CNN "Comment"
	1    3500 5550
	0    1    1    0   
$EndComp
$Comp
L Device:R R2
U 1 1 60252DAE
P 3550 6250
F 0 "R2" V 3343 6250 50  0000 C CNN
F 1 "1.2K" V 3434 6250 50  0000 C CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal" V 3480 6250 50  0001 C CNN
F 3 "~" H 3550 6250 50  0001 C CNN
F 4 "For SIO LED" V 3550 6250 50  0001 C CNN "Comment"
	1    3550 6250
	0    1    1    0   
$EndComp
$Comp
L Device:R R3
U 1 1 60252E7C
P 3550 6950
F 0 "R3" V 3343 6950 50  0000 C CNN
F 1 "1K" V 3434 6950 50  0000 C CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal" V 3480 6950 50  0001 C CNN
F 3 "~" H 3550 6950 50  0001 C CNN
F 4 "For bluetooth LED" V 3550 6950 50  0001 C CNN "Comment"
	1    3550 6950
	0    1    1    0   
$EndComp
Text GLabel 7550 2900 2    50   Input ~ 0
IO2_LED1
$Comp
L Device:R R6
U 1 1 602584CC
P 8950 1100
F 0 "R6" H 8880 1054 50  0000 R CNN
F 1 "10K" H 8880 1145 50  0000 R CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal" V 8880 1100 50  0001 C CNN
F 3 "~" H 8950 1100 50  0001 C CNN
	1    8950 1100
	-1   0    0    1   
$EndComp
$Comp
L Device:R R4
U 1 1 6025909A
P 9250 1100
F 0 "R4" H 9180 1054 50  0000 R CNN
F 1 "10K" H 9180 1145 50  0000 R CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal" V 9180 1100 50  0001 C CNN
F 3 "~" H 9250 1100 50  0001 C CNN
	1    9250 1100
	-1   0    0    1   
$EndComp
$Comp
L Device:R R7
U 1 1 6025A5E7
P 3650 4850
F 0 "R7" V 3443 4850 50  0000 C CNN
F 1 "470" V 3534 4850 50  0000 C CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal" V 3580 4850 50  0001 C CNN
F 3 "~" H 3650 4850 50  0001 C CNN
	1    3650 4850
	0    1    1    0   
$EndComp
$Comp
L Device:R R9
U 1 1 6025B630
P 10150 1100
F 0 "R9" H 10220 1146 50  0000 L CNN
F 1 "10K" H 10220 1055 50  0000 L CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal" V 10080 1100 50  0001 C CNN
F 3 "~" H 10150 1100 50  0001 C CNN
	1    10150 1100
	1    0    0    -1  
$EndComp
$Comp
L Device:R R8
U 1 1 6025C078
P 9850 1100
F 0 "R8" H 9780 1054 50  0000 R CNN
F 1 "10K" H 9780 1145 50  0000 R CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal" V 9780 1100 50  0001 C CNN
F 3 "~" H 9850 1100 50  0001 C CNN
	1    9850 1100
	-1   0    0    1   
$EndComp
$Comp
L Device:R R5
U 1 1 6025C39F
P 9550 1100
F 0 "R5" H 9480 1054 50  0000 R CNN
F 1 "10K" H 9480 1145 50  0000 R CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal" V 9480 1100 50  0001 C CNN
F 3 "~" H 9550 1100 50  0001 C CNN
	1    9550 1100
	-1   0    0    1   
$EndComp
$Comp
L Switch:SW_MEC_5E SW2
U 1 1 6025DBD3
P 5950 4800
F 0 "SW2" H 5950 5185 50  0000 C CNN
F 1 "BUTTON B" H 5950 5094 50  0000 C CNN
F 2 "Button_Switch_THT:SW_TH_Tactile_Omron_B3F-10xx" H 5950 5100 50  0001 C CNN
F 3 "http://www.apem.com/int/index.php?controller=attachment&id_attachment=1371" H 5950 5100 50  0001 C CNN
	1    5950 4800
	1    0    0    -1  
$EndComp
$Comp
L Switch:SW_MEC_5E SW3
U 1 1 6025E7FC
P 5950 5550
F 0 "SW3" H 5950 5935 50  0000 C CNN
F 1 "RESET" H 5950 5844 50  0000 C CNN
F 2 "Button_Switch_THT:SW_TH_Tactile_Omron_B3F-10xx" H 5950 5850 50  0001 C CNN
F 3 "http://www.apem.com/int/index.php?controller=attachment&id_attachment=1371" H 5950 5850 50  0001 C CNN
	1    5950 5550
	1    0    0    -1  
$EndComp
$Comp
L Connector_Generic:Conn_01x12 J1
U 1 1 602630DD
P 950 1700
F 0 "J1" H 868 875 50  0000 C CNN
F 1 "SIO (No 12V)" H 868 966 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x12_P2.54mm_Vertical" H 950 1700 50  0001 C CNN
F 3 "~" H 950 1700 50  0001 C CNN
F 4 "No Pin 12, Pin 13 SIO = Pin 12 on header" H 950 1700 50  0001 C CNN "Comment"
	1    950  1700
	-1   0    0    1   
$EndComp
$Comp
L Device:C C1
U 1 1 60269C82
P 3350 4850
F 0 "C1" V 3602 4850 50  0000 C CNN
F 1 "4.7uF 6.3V" V 3511 4850 50  0000 C CNN
F 2 "Capacitor_THT:C_Disc_D5.1mm_W3.2mm_P5.00mm" H 3350 4850 50  0001 C CNN
F 3 "~" H 3350 4850 50  0001 C CNN
	1    3350 4850
	0    -1   -1   0   
$EndComp
$Comp
L Device:C C2
U 1 1 6027D836
P 800 5950
F 0 "C2" H 915 5996 50  0000 L CNN
F 1 "0.1uf" H 915 5905 50  0000 L CNN
F 2 "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm" H 838 5800 50  0001 C CNN
F 3 "~" H 800 5950 50  0001 C CNN
	1    800  5950
	1    0    0    -1  
$EndComp
$Comp
L Device:C C3
U 1 1 6027DCE6
P 1250 5950
F 0 "C3" H 1365 5996 50  0000 L CNN
F 1 "0.1uf" H 1365 5905 50  0000 L CNN
F 2 "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm" H 1288 5800 50  0001 C CNN
F 3 "~" H 1250 5950 50  0001 C CNN
	1    1250 5950
	1    0    0    -1  
$EndComp
$Comp
L Device:R R10
U 1 1 602911ED
P 8050 4650
F 0 "R10" H 7980 4604 50  0000 R CNN
F 1 "10K" H 7980 4695 50  0000 R CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal" V 7980 4650 50  0001 C CNN
F 3 "~" H 8050 4650 50  0001 C CNN
F 4 "Optional, pull-up when using SMD SD connector" H 8050 4650 50  0001 C CNN "Comment"
	1    8050 4650
	-1   0    0    1   
$EndComp
$Comp
L Device:R R11
U 1 1 60291316
P 8350 4650
F 0 "R11" H 8280 4604 50  0000 R CNN
F 1 "10K" H 8280 4695 50  0000 R CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal" V 8280 4650 50  0001 C CNN
F 3 "~" H 8350 4650 50  0001 C CNN
F 4 "Optional, pull-up when using SMD SD connector" H 8350 4650 50  0001 C CNN "Comment"
	1    8350 4650
	-1   0    0    1   
$EndComp
$Comp
L Device:R R12
U 1 1 6029140B
P 8650 4650
F 0 "R12" H 8580 4604 50  0000 R CNN
F 1 "10K" H 8580 4695 50  0000 R CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal" V 8580 4650 50  0001 C CNN
F 3 "~" H 8650 4650 50  0001 C CNN
F 4 "Optional, pull-up when using SMD SD connector" H 8650 4650 50  0001 C CNN "Comment"
	1    8650 4650
	-1   0    0    1   
$EndComp
$Comp
L Device:R R13
U 1 1 602914FA
P 8950 4650
F 0 "R13" H 8880 4604 50  0000 R CNN
F 1 "10K" H 8880 4695 50  0000 R CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal" V 8880 4650 50  0001 C CNN
F 3 "~" H 8950 4650 50  0001 C CNN
F 4 "Optional, pull-up when using SMD SD connector" H 8950 4650 50  0001 C CNN "Comment"
	1    8950 4650
	-1   0    0    1   
$EndComp
$Comp
L Connector_Generic:Conn_01x06 J3
U 1 1 60296E69
P 10150 3550
F 0 "J3" H 10230 3542 50  0000 L CNN
F 1 "SD BOARD" H 10230 3451 50  0000 L CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical" H 10150 3550 50  0001 C CNN
F 3 "~" H 10150 3550 50  0001 C CNN
F 4 "For Aliexpress MicroSD module if not using SMD footprint" H 10150 3550 50  0001 C CNN "Comment"
	1    10150 3550
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR0101
U 1 1 602A15C6
P 3150 4300
F 0 "#PWR0101" H 3150 4050 50  0001 C CNN
F 1 "GND" H 3155 4127 50  0000 C CNN
F 2 "" H 3150 4300 50  0001 C CNN
F 3 "" H 3150 4300 50  0001 C CNN
	1    3150 4300
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR0102
U 1 1 602A23A8
P 1150 1900
F 0 "#PWR0102" H 1150 1650 50  0001 C CNN
F 1 "GND" V 1155 1772 50  0000 R CNN
F 2 "" H 1150 1900 50  0001 C CNN
F 3 "" H 1150 1900 50  0001 C CNN
	1    1150 1900
	0    -1   -1   0   
$EndComp
$Comp
L power:GND #PWR0103
U 1 1 602A358F
P 1150 1700
F 0 "#PWR0103" H 1150 1450 50  0001 C CNN
F 1 "GND" V 1155 1572 50  0000 R CNN
F 2 "" H 1150 1700 50  0001 C CNN
F 3 "" H 1150 1700 50  0001 C CNN
	1    1150 1700
	0    -1   -1   0   
$EndComp
$Comp
L power:+5V #PWR0105
U 1 1 602A6267
P 3150 3300
F 0 "#PWR0105" H 3150 3150 50  0001 C CNN
F 1 "+5V" H 3165 3473 50  0000 C CNN
F 2 "" H 3150 3300 50  0001 C CNN
F 3 "" H 3150 3300 50  0001 C CNN
	1    3150 3300
	1    0    0    -1  
$EndComp
$Comp
L power:+5V #PWR0106
U 1 1 602A7178
P 1250 5800
F 0 "#PWR0106" H 1250 5650 50  0001 C CNN
F 1 "+5V" H 1265 5973 50  0000 C CNN
F 2 "" H 1250 5800 50  0001 C CNN
F 3 "" H 1250 5800 50  0001 C CNN
	1    1250 5800
	1    0    0    -1  
$EndComp
$Comp
L power:+5V #PWR0107
U 1 1 602A8113
P 800 5800
F 0 "#PWR0107" H 800 5650 50  0001 C CNN
F 1 "+5V" H 815 5973 50  0000 C CNN
F 2 "" H 800 5800 50  0001 C CNN
F 3 "" H 800 5800 50  0001 C CNN
	1    800  5800
	1    0    0    -1  
$EndComp
$Comp
L power:+5V #PWR0108
U 1 1 602AD537
P 4050 3300
F 0 "#PWR0108" H 4050 3150 50  0001 C CNN
F 1 "+5V" H 4065 3473 50  0000 C CNN
F 2 "" H 4050 3300 50  0001 C CNN
F 3 "" H 4050 3300 50  0001 C CNN
	1    4050 3300
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR0109
U 1 1 602AEA29
P 4050 4300
F 0 "#PWR0109" H 4050 4050 50  0001 C CNN
F 1 "GND" H 4055 4127 50  0000 C CNN
F 2 "" H 4050 4300 50  0001 C CNN
F 3 "" H 4050 4300 50  0001 C CNN
	1    4050 4300
	1    0    0    -1  
$EndComp
Text GLabel 1150 2200 2    50   Input ~ 0
SIO_CKIN
Text GLabel 1150 2100 2    50   Input ~ 0
SIO_CKOUT
Text GLabel 1150 2000 2    50   Input ~ 0
SIO_DATAIN
Text GLabel 1150 1800 2    50   Input ~ 0
SIO_DATAOUT
Text GLabel 1150 1600 2    50   Input ~ 0
SIO_CMD
Text GLabel 1150 1500 2    50   Input ~ 0
SIO_MCTL
Text GLabel 1150 1400 2    50   Input ~ 0
SIO_PROC
Text GLabel 1150 1200 2    50   Input ~ 0
SIO_AUDIOIN
Text GLabel 1150 1100 2    50   Input ~ 0
SIO_INT
$Comp
L 74xx:SN74LS07N U3
U 2 1 602BAA74
P 2550 1500
F 0 "U3" H 2550 1817 50  0000 C CNN
F 1 "SN74LS07N" H 2550 1726 50  0000 C CNN
F 2 "Package_DIP:DIP-14_W7.62mm_Socket_LongPads" H 2550 1500 50  0001 C CNN
F 3 "www.ti.com/lit/ds/symlink/sn74ls07.pdf" H 2550 1500 50  0001 C CNN
	2    2550 1500
	1    0    0    -1  
$EndComp
$Comp
L 74xx:SN74LS07N U3
U 3 1 602BB334
P 2550 1850
F 0 "U3" H 2550 2167 50  0000 C CNN
F 1 "SN74LS07N" H 2550 2076 50  0000 C CNN
F 2 "Package_DIP:DIP-14_W7.62mm_Socket_LongPads" H 2550 1850 50  0001 C CNN
F 3 "www.ti.com/lit/ds/symlink/sn74ls07.pdf" H 2550 1850 50  0001 C CNN
	3    2550 1850
	1    0    0    -1  
$EndComp
$Comp
L 74xx:SN74LS07N U3
U 4 1 602BC267
P 2550 2200
F 0 "U3" H 2550 2517 50  0000 C CNN
F 1 "SN74LS07N" H 2550 2426 50  0000 C CNN
F 2 "Package_DIP:DIP-14_W7.62mm_Socket_LongPads" H 2550 2200 50  0001 C CNN
F 3 "www.ti.com/lit/ds/symlink/sn74ls07.pdf" H 2550 2200 50  0001 C CNN
	4    2550 2200
	1    0    0    -1  
$EndComp
$Comp
L 74xx:SN74LS07N U3
U 5 1 602BE803
P 2550 2550
F 0 "U3" H 2550 2867 50  0000 C CNN
F 1 "SN74LS07N" H 2550 2776 50  0000 C CNN
F 2 "Package_DIP:DIP-14_W7.62mm_Socket_LongPads" H 2550 2550 50  0001 C CNN
F 3 "www.ti.com/lit/ds/symlink/sn74ls07.pdf" H 2550 2550 50  0001 C CNN
	5    2550 2550
	1    0    0    -1  
$EndComp
$Comp
L 74xx:SN74LS07N U3
U 6 1 602BF3DA
P 2550 2900
F 0 "U3" H 2550 3217 50  0000 C CNN
F 1 "SN74LS07N" H 2550 3126 50  0000 C CNN
F 2 "Package_DIP:DIP-14_W7.62mm_Socket_LongPads" H 2550 2900 50  0001 C CNN
F 3 "www.ti.com/lit/ds/symlink/sn74ls07.pdf" H 2550 2900 50  0001 C CNN
	6    2550 2900
	1    0    0    -1  
$EndComp
Text GLabel 3900 2900 0    50   Input ~ 0
SIO_CMD
Text GLabel 2250 2550 0    50   Input ~ 0
IO22_PROC
Text GLabel 3900 1500 0    50   Input ~ 0
IO26_INT
$Comp
L power:GND #PWR0113
U 1 1 602D7AED
P 800 6100
F 0 "#PWR0113" H 800 5850 50  0001 C CNN
F 1 "GND" H 805 5927 50  0000 C CNN
F 2 "" H 800 6100 50  0001 C CNN
F 3 "" H 800 6100 50  0001 C CNN
	1    800  6100
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR0114
U 1 1 602D8150
P 1250 6100
F 0 "#PWR0114" H 1250 5850 50  0001 C CNN
F 1 "GND" H 1255 5927 50  0000 C CNN
F 2 "" H 1250 6100 50  0001 C CNN
F 3 "" H 1250 6100 50  0001 C CNN
	1    1250 6100
	1    0    0    -1  
$EndComp
Text GLabel 8950 1250 3    50   Input ~ 0
IO39_CMD
Text GLabel 4500 2900 2    50   Input ~ 0
IO39_CMD
Text GLabel 5950 1800 0    50   Input ~ 0
IO39_CMD
$Comp
L power:+3.3V #PWR0115
U 1 1 602DD1BA
P 8950 950
F 0 "#PWR0115" H 8950 800 50  0001 C CNN
F 1 "+3.3V" H 8965 1123 50  0000 C CNN
F 2 "" H 8950 950 50  0001 C CNN
F 3 "" H 8950 950 50  0001 C CNN
	1    8950 950 
	1    0    0    -1  
$EndComp
Text GLabel 2850 2550 2    50   Input ~ 0
SIO_PROC
Text GLabel 4500 1500 2    50   Input ~ 0
SIO_INT
$Comp
L 74xx:SN74LS07N U4
U 2 1 602DF200
P 4200 1500
F 0 "U4" H 4200 1817 50  0000 C CNN
F 1 "SN74LS07N" H 4200 1726 50  0000 C CNN
F 2 "Package_DIP:DIP-14_W7.62mm_Socket_LongPads" H 4200 1500 50  0001 C CNN
F 3 "www.ti.com/lit/ds/symlink/sn74ls07.pdf" H 4200 1500 50  0001 C CNN
	2    4200 1500
	1    0    0    -1  
$EndComp
$Comp
L 74xx:SN74LS07N U4
U 3 1 602E0C15
P 4200 1850
F 0 "U4" H 4200 2167 50  0000 C CNN
F 1 "SN74LS07N" H 4200 2076 50  0000 C CNN
F 2 "Package_DIP:DIP-14_W7.62mm_Socket_LongPads" H 4200 1850 50  0001 C CNN
F 3 "www.ti.com/lit/ds/symlink/sn74ls07.pdf" H 4200 1850 50  0001 C CNN
	3    4200 1850
	1    0    0    -1  
$EndComp
$Comp
L 74xx:SN74LS07N U4
U 4 1 602E2275
P 4200 2200
F 0 "U4" H 4200 2517 50  0000 C CNN
F 1 "SN74LS07N" H 4200 2426 50  0000 C CNN
F 2 "Package_DIP:DIP-14_W7.62mm_Socket_LongPads" H 4200 2200 50  0001 C CNN
F 3 "www.ti.com/lit/ds/symlink/sn74ls07.pdf" H 4200 2200 50  0001 C CNN
	4    4200 2200
	1    0    0    -1  
$EndComp
$Comp
L 74xx:SN74LS07N U4
U 5 1 602E3B1D
P 4200 2550
F 0 "U4" H 4200 2867 50  0000 C CNN
F 1 "SN74LS07N" H 4200 2776 50  0000 C CNN
F 2 "Package_DIP:DIP-14_W7.62mm_Socket_LongPads" H 4200 2550 50  0001 C CNN
F 3 "www.ti.com/lit/ds/symlink/sn74ls07.pdf" H 4200 2550 50  0001 C CNN
	5    4200 2550
	1    0    0    -1  
$EndComp
$Comp
L 74xx:SN74LS07N U4
U 6 1 602E53A1
P 4200 2900
F 0 "U4" H 4200 3217 50  0000 C CNN
F 1 "SN74LS07N" H 4200 3126 50  0000 C CNN
F 2 "Package_DIP:DIP-14_W7.62mm_Socket_LongPads" H 4200 2900 50  0001 C CNN
F 3 "www.ti.com/lit/ds/symlink/sn74ls07.pdf" H 4200 2900 50  0001 C CNN
	6    4200 2900
	1    0    0    -1  
$EndComp
Text GLabel 3900 1850 0    50   Input ~ 0
IO27_CKIN
Text GLabel 4500 2550 2    50   Input ~ 0
IO32_CKOUT
Text GLabel 2250 2200 0    50   Input ~ 0
IO21_DATAIN
Text GLabel 4500 2200 2    50   Input ~ 0
IO33_DATAOUT
Text GLabel 4500 1850 2    50   Input ~ 0
SIO_CKIN
Text GLabel 3900 2550 0    50   Input ~ 0
SIO_CKOUT
Text GLabel 2850 2200 2    50   Input ~ 0
SIO_DATAIN
Text GLabel 3900 2200 0    50   Input ~ 0
SIO_DATAOUT
Text GLabel 5950 1700 0    50   Input ~ 0
SIO_MCTL
Text GLabel 9250 1250 3    50   Input ~ 0
SIO_MCTL
$Comp
L power:GND #PWR0118
U 1 1 602F8E83
P 9250 950
F 0 "#PWR0118" H 9250 700 50  0001 C CNN
F 1 "GND" H 9255 777 50  0000 C CNN
F 2 "" H 9250 950 50  0001 C CNN
F 3 "" H 9250 950 50  0001 C CNN
	1    9250 950 
	-1   0    0    1   
$EndComp
Text GLabel 5950 1900 0    50   Input ~ 0
IO34_BUTTON_B
Text GLabel 9550 1250 3    50   Input ~ 0
IO34_BUTTON_B
$Comp
L power:+3.3V #PWR0119
U 1 1 602FACA8
P 9550 950
F 0 "#PWR0119" H 9550 800 50  0001 C CNN
F 1 "+3.3V" H 9565 1123 50  0000 C CNN
F 2 "" H 9550 950 50  0001 C CNN
F 3 "" H 9550 950 50  0001 C CNN
	1    9550 950 
	1    0    0    -1  
$EndComp
Text GLabel 5750 4700 0    50   Input ~ 0
IO34_BUTTON_B
$Comp
L power:GND #PWR0120
U 1 1 602FCBD3
P 6150 4700
F 0 "#PWR0120" H 6150 4450 50  0001 C CNN
F 1 "GND" V 6155 4572 50  0000 R CNN
F 2 "" H 6150 4700 50  0001 C CNN
F 3 "" H 6150 4700 50  0001 C CNN
	1    6150 4700
	0    -1   -1   0   
$EndComp
$Comp
L power:GND #PWR0121
U 1 1 602FD882
P 6150 4000
F 0 "#PWR0121" H 6150 3750 50  0001 C CNN
F 1 "GND" V 6155 3872 50  0000 R CNN
F 2 "" H 6150 4000 50  0001 C CNN
F 3 "" H 6150 4000 50  0001 C CNN
	1    6150 4000
	0    -1   -1   0   
$EndComp
$Comp
L power:GND #PWR0122
U 1 1 602FDD70
P 6150 5450
F 0 "#PWR0122" H 6150 5200 50  0001 C CNN
F 1 "GND" V 6155 5322 50  0000 R CNN
F 2 "" H 6150 5450 50  0001 C CNN
F 3 "" H 6150 5450 50  0001 C CNN
	1    6150 5450
	0    -1   -1   0   
$EndComp
Text GLabel 5950 2000 0    50   Input ~ 0
IO35_SIO_VOLTAGE
Text GLabel 9400 2550 0    50   Input ~ 0
IO35_SIO_VOLTAGE
$Comp
L Device:R R14
U 1 1 602FEA6E
P 9550 2400
F 0 "R14" H 9480 2354 50  0000 R CNN
F 1 "2K" H 9480 2445 50  0000 R CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal" V 9480 2400 50  0001 C CNN
F 3 "~" H 9550 2400 50  0001 C CNN
F 4 "Optional, only used to show SIO voltage in web UI" H 9550 2400 50  0001 C CNN "Comment"
	1    9550 2400
	-1   0    0    1   
$EndComp
$Comp
L Device:R R15
U 1 1 602FF394
P 9550 2700
F 0 "R15" H 9480 2654 50  0000 R CNN
F 1 "3.9K" H 9480 2745 50  0000 R CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal" V 9480 2700 50  0001 C CNN
F 3 "~" H 9550 2700 50  0001 C CNN
F 4 "Optional, only used to show SIO voltage in web UI" H 9550 2700 50  0001 C CNN "Comment"
	1    9550 2700
	-1   0    0    1   
$EndComp
$Comp
L power:+5V #PWR0123
U 1 1 60300545
P 9550 2250
F 0 "#PWR0123" H 9550 2100 50  0001 C CNN
F 1 "+5V" H 9565 2423 50  0000 C CNN
F 2 "" H 9550 2250 50  0001 C CNN
F 3 "" H 9550 2250 50  0001 C CNN
	1    9550 2250
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR0124
U 1 1 60301355
P 9550 2850
F 0 "#PWR0124" H 9550 2600 50  0001 C CNN
F 1 "GND" H 9555 2677 50  0000 C CNN
F 2 "" H 9550 2850 50  0001 C CNN
F 3 "" H 9550 2850 50  0001 C CNN
	1    9550 2850
	1    0    0    -1  
$EndComp
$Comp
L power:+3.3V #PWR0125
U 1 1 60301D9A
P 5950 1500
F 0 "#PWR0125" H 5950 1350 50  0001 C CNN
F 1 "+3.3V" H 5965 1673 50  0000 C CNN
F 2 "" H 5950 1500 50  0001 C CNN
F 3 "" H 5950 1500 50  0001 C CNN
	1    5950 1500
	1    0    0    -1  
$EndComp
Text GLabel 5950 2100 0    50   Input ~ 0
IO32_CKOUT
Text GLabel 5950 2200 0    50   Input ~ 0
IO33_DATAOUT
Text GLabel 5950 2300 0    50   Input ~ 0
IO25_AUDIOIN
Text GLabel 3800 4850 2    50   Input ~ 0
IO25_AUDIOIN
Text GLabel 3200 4850 0    50   Input ~ 0
SIO_AUDIOIN
Text GLabel 5950 2400 0    50   Input ~ 0
IO26_INT
Text GLabel 5950 2500 0    50   Input ~ 0
IO27_CKIN
Text GLabel 5950 2600 0    50   Input ~ 0
IO14_BUTTON_RESET
Text GLabel 9850 1250 3    50   Input ~ 0
IO14_BUTTON_RESET
Text GLabel 5750 5450 0    50   Input ~ 0
IO14_BUTTON_RESET
$Comp
L power:+3.3V #PWR0126
U 1 1 603094E5
P 9850 950
F 0 "#PWR0126" H 9850 800 50  0001 C CNN
F 1 "+3.3V" H 9865 1123 50  0000 C CNN
F 2 "" H 9850 950 50  0001 C CNN
F 3 "" H 9850 950 50  0001 C CNN
	1    9850 950 
	1    0    0    -1  
$EndComp
Text GLabel 7550 2800 2    50   Input ~ 0
IO0_BUTTON_A
Text GLabel 10150 1250 3    50   Input ~ 0
IO0_BUTTON_A
$Comp
L power:+3.3V #PWR0127
U 1 1 6030B482
P 10150 950
F 0 "#PWR0127" H 10150 800 50  0001 C CNN
F 1 "+3.3V" H 10165 1123 50  0000 C CNN
F 2 "" H 10150 950 50  0001 C CNN
F 3 "" H 10150 950 50  0001 C CNN
	1    10150 950 
	1    0    0    -1  
$EndComp
Text GLabel 3350 5550 0    50   Input ~ 0
IO2_LED1
Wire Wire Line
	9400 2550 9550 2550
Connection ~ 9550 2550
Text GLabel 7550 2700 2    50   Input ~ 0
IO4_LED2
Text GLabel 3400 6250 0    50   Input ~ 0
IO4_LED2
Text GLabel 7550 1700 2    50   Input ~ 0
IO22_PROC
Text GLabel 7550 2000 2    50   Input ~ 0
IO21_DATAIN
$Comp
L power:GND #PWR0128
U 1 1 6030EB71
P 7550 1500
F 0 "#PWR0128" H 7550 1250 50  0001 C CNN
F 1 "GND" H 7555 1327 50  0000 C CNN
F 2 "" H 7550 1500 50  0001 C CNN
F 3 "" H 7550 1500 50  0001 C CNN
	1    7550 1500
	-1   0    0    1   
$EndComp
$Comp
L power:GND #PWR0129
U 1 1 6030F47E
P 7550 2100
F 0 "#PWR0129" H 7550 1850 50  0001 C CNN
F 1 "GND" V 7555 1972 50  0000 R CNN
F 2 "" H 7550 2100 50  0001 C CNN
F 3 "" H 7550 2100 50  0001 C CNN
	1    7550 2100
	0    -1   -1   0   
$EndComp
$Comp
L power:GND #PWR0130
U 1 1 6030FCF2
P 5950 2800
F 0 "#PWR0130" H 5950 2550 50  0001 C CNN
F 1 "GND" V 5955 2672 50  0000 R CNN
F 2 "" H 5950 2800 50  0001 C CNN
F 3 "" H 5950 2800 50  0001 C CNN
	1    5950 2800
	0    1    1    0   
$EndComp
Text GLabel 5750 4000 0    50   Input ~ 0
IO0_BUTTON_A
Text GLabel 3400 6950 0    50   Input ~ 0
IO3_LED3
Text GLabel 5950 2900 0    50   Input ~ 0
IO3_LED3
Wire Wire Line
	3650 5550 3900 5550
Wire Wire Line
	3700 6250 3900 6250
Wire Wire Line
	3700 6950 3900 6950
$Comp
L power:+3.3V #PWR0131
U 1 1 6031261E
P 4200 5550
F 0 "#PWR0131" H 4200 5400 50  0001 C CNN
F 1 "+3.3V" V 4215 5678 50  0000 L CNN
F 2 "" H 4200 5550 50  0001 C CNN
F 3 "" H 4200 5550 50  0001 C CNN
	1    4200 5550
	0    1    1    0   
$EndComp
$Comp
L power:+3.3V #PWR0132
U 1 1 6031315C
P 4200 6250
F 0 "#PWR0132" H 4200 6100 50  0001 C CNN
F 1 "+3.3V" V 4215 6378 50  0000 L CNN
F 2 "" H 4200 6250 50  0001 C CNN
F 3 "" H 4200 6250 50  0001 C CNN
	1    4200 6250
	0    1    1    0   
$EndComp
$Comp
L power:+3.3V #PWR0133
U 1 1 6031359A
P 4200 6950
F 0 "#PWR0133" H 4200 6800 50  0001 C CNN
F 1 "+3.3V" V 4215 7078 50  0000 L CNN
F 2 "" H 4200 6950 50  0001 C CNN
F 3 "" H 4200 6950 50  0001 C CNN
	1    4200 6950
	0    1    1    0   
$EndComp
$Comp
L power:+3.3V #PWR0134
U 1 1 60314994
P 9950 3350
F 0 "#PWR0134" H 9950 3200 50  0001 C CNN
F 1 "+3.3V" H 9965 3523 50  0000 C CNN
F 2 "" H 9950 3350 50  0001 C CNN
F 3 "" H 9950 3350 50  0001 C CNN
	1    9950 3350
	1    0    0    -1  
$EndComp
Text GLabel 7550 2400 2    50   Input ~ 0
IO5_SPI_CS
Text GLabel 9950 3450 0    50   Input ~ 0
IO5_SPI_CS
Text GLabel 7550 2300 2    50   Input ~ 0
IO18_SPI_CLK
Text GLabel 9950 3650 0    50   Input ~ 0
IO18_SPI_CLK
$Comp
L power:GND #PWR0135
U 1 1 603180DE
P 9950 3850
F 0 "#PWR0135" H 9950 3600 50  0001 C CNN
F 1 "GND" H 9955 3677 50  0000 C CNN
F 2 "" H 9950 3850 50  0001 C CNN
F 3 "" H 9950 3850 50  0001 C CNN
	1    9950 3850
	1    0    0    -1  
$EndComp
Text GLabel 7550 1600 2    50   Input ~ 0
IO23_SPI_MOSI
Text GLabel 9950 3550 0    50   Input ~ 0
IO23_SPI_MOSI
Text GLabel 7550 2200 2    50   Input ~ 0
IO19_SPI_MISO
Text GLabel 9950 3750 0    50   Input ~ 0
IO19_SPI_MISO
$Comp
L power:+5V #PWR0136
U 1 1 6032232E
P 5950 3300
F 0 "#PWR0136" H 5950 3150 50  0001 C CNN
F 1 "+5V" H 5965 3473 50  0000 C CNN
F 2 "" H 5950 3300 50  0001 C CNN
F 3 "" H 5950 3300 50  0001 C CNN
	1    5950 3300
	-1   0    0    1   
$EndComp
Text GLabel 7850 5400 0    50   Input ~ 0
IO19_SPI_MISO
Text GLabel 7850 5700 0    50   Input ~ 0
IO5_SPI_CS
Text GLabel 7850 5300 0    50   Input ~ 0
IO23_SPI_MOSI
Text GLabel 7850 5100 0    50   Input ~ 0
IO18_SPI_CLK
$Comp
L power:+3.3V #PWR0139
U 1 1 60347F4F
P 8050 4500
F 0 "#PWR0139" H 8050 4350 50  0001 C CNN
F 1 "+3.3V" V 8065 4628 50  0000 L CNN
F 2 "" H 8050 4500 50  0001 C CNN
F 3 "" H 8050 4500 50  0001 C CNN
	1    8050 4500
	1    0    0    -1  
$EndComp
$Comp
L power:+3.3V #PWR0140
U 1 1 603489F5
P 8350 4500
F 0 "#PWR0140" H 8350 4350 50  0001 C CNN
F 1 "+3.3V" V 8365 4628 50  0000 L CNN
F 2 "" H 8350 4500 50  0001 C CNN
F 3 "" H 8350 4500 50  0001 C CNN
	1    8350 4500
	1    0    0    -1  
$EndComp
$Comp
L power:+3.3V #PWR0141
U 1 1 60348C77
P 8650 4500
F 0 "#PWR0141" H 8650 4350 50  0001 C CNN
F 1 "+3.3V" V 8665 4628 50  0000 L CNN
F 2 "" H 8650 4500 50  0001 C CNN
F 3 "" H 8650 4500 50  0001 C CNN
	1    8650 4500
	1    0    0    -1  
$EndComp
$Comp
L power:+3.3V #PWR0142
U 1 1 60348F10
P 8950 4500
F 0 "#PWR0142" H 8950 4350 50  0001 C CNN
F 1 "+3.3V" V 8965 4628 50  0000 L CNN
F 2 "" H 8950 4500 50  0001 C CNN
F 3 "" H 8950 4500 50  0001 C CNN
	1    8950 4500
	1    0    0    -1  
$EndComp
$Comp
L Mechanical:MountingHole H1
U 1 1 6039E0F0
P 6150 6900
F 0 "H1" H 6250 6946 50  0000 L CNN
F 1 "M3 Mounting Hole" H 6250 6855 50  0000 L CNN
F 2 "MountingHole:MountingHole_3.2mm_M3" H 6150 6900 50  0001 C CNN
F 3 "~" H 6150 6900 50  0001 C CNN
	1    6150 6900
	1    0    0    -1  
$EndComp
$Comp
L Mechanical:MountingHole H2
U 1 1 6039E9FF
P 6150 7100
F 0 "H2" H 6250 7146 50  0000 L CNN
F 1 "M3 Mounting Hole" H 6250 7055 50  0000 L CNN
F 2 "MountingHole:MountingHole_3.2mm_M3" H 6150 7100 50  0001 C CNN
F 3 "~" H 6150 7100 50  0001 C CNN
	1    6150 7100
	1    0    0    -1  
$EndComp
$Comp
L Mechanical:MountingHole H3
U 1 1 603A0284
P 6150 7300
F 0 "H3" H 6250 7346 50  0000 L CNN
F 1 "M3 Mounting Hole" H 6250 7255 50  0000 L CNN
F 2 "MountingHole:MountingHole_3.2mm_M3" H 6150 7300 50  0001 C CNN
F 3 "~" H 6150 7300 50  0001 C CNN
	1    6150 7300
	1    0    0    -1  
$EndComp
$Comp
L Mechanical:MountingHole H4
U 1 1 603A0A21
P 6150 7500
F 0 "H4" H 6250 7546 50  0000 L CNN
F 1 "M3 Mounting Hole" H 6250 7455 50  0000 L CNN
F 2 "MountingHole:MountingHole_3.2mm_M3" H 6150 7500 50  0001 C CNN
F 3 "~" H 6150 7500 50  0001 C CNN
	1    6150 7500
	1    0    0    -1  
$EndComp
$Comp
L ST-TF-003A:ST-TF-003A P1
U 1 1 603D8B5F
P 10100 5400
F 0 "P1" H 10530 5446 50  0000 L CNN
F 1 "ST-TF-003A" H 10530 5355 50  0000 L CNN
F 2 "ST-TF-003A:SUNTECH_ST-TF-003A" H 10100 5400 50  0001 L BNN
F 3 "" H 10100 5400 50  0001 L BNN
F 4 "Suntech" H 10100 5400 50  0001 L BNN "MANUFACTURER"
	1    10100 5400
	1    0    0    -1  
$EndComp
$Comp
L Connector_Generic:Conn_01x02 J2
U 1 1 6040A189
P 6000 4300
F 0 "J2" V 5872 4380 50  0000 L CNN
F 1 "Conn_BUTTON_A" V 5963 4380 50  0000 L CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 6000 4300 50  0001 C CNN
F 3 "~" H 6000 4300 50  0001 C CNN
F 4 "Optional, Button A header" V 6000 4300 50  0001 C CNN "Comment"
	1    6000 4300
	0    1    1    0   
$EndComp
$Comp
L Connector_Generic:Conn_01x02 J4
U 1 1 6040ACC6
P 6000 5000
F 0 "J4" V 5872 5080 50  0000 L CNN
F 1 "Conn_BUTTON_B" V 5963 5080 50  0000 L CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 6000 5000 50  0001 C CNN
F 3 "~" H 6000 5000 50  0001 C CNN
F 4 "Optional, Button B header" V 6000 5000 50  0001 C CNN "Comment"
	1    6000 5000
	0    1    1    0   
$EndComp
$Comp
L Connector_Generic:Conn_01x02 J5
U 1 1 6040B335
P 6000 5750
F 0 "J5" V 5872 5830 50  0000 L CNN
F 1 "Conn_BUTTON_RESET" V 5963 5830 50  0000 L CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 6000 5750 50  0001 C CNN
F 3 "~" H 6000 5750 50  0001 C CNN
F 4 "Optional, Reset button header" V 6000 5750 50  0001 C CNN "Comment"
	1    6000 5750
	0    1    1    0   
$EndComp
$Comp
L Connector_Generic:Conn_01x02 J6
U 1 1 6040B945
P 4100 5900
F 0 "J6" V 3972 5980 50  0000 L CNN
F 1 "Conn_WHITE_LED" V 4063 5980 50  0000 L CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 4100 5900 50  0001 C CNN
F 3 "~" H 4100 5900 50  0001 C CNN
F 4 "Optional, Wifi LED header" V 4100 5900 50  0001 C CNN "Comment"
	1    4100 5900
	0    1    1    0   
$EndComp
$Comp
L Connector_Generic:Conn_01x02 J7
U 1 1 60418972
P 4100 6600
F 0 "J7" V 3972 6680 50  0000 L CNN
F 1 "Conn_ORANGE_LED" V 4063 6680 50  0000 L CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 4100 6600 50  0001 C CNN
F 3 "~" H 4100 6600 50  0001 C CNN
F 4 "Optional, SIO LED header" V 4100 6600 50  0001 C CNN "Comment"
	1    4100 6600
	0    1    1    0   
$EndComp
$Comp
L Connector_Generic:Conn_01x02 J8
U 1 1 60419D2F
P 4100 7300
F 0 "J8" V 3972 7380 50  0000 L CNN
F 1 "Conn_BLUE_LED" V 4063 7380 50  0000 L CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 4100 7300 50  0001 C CNN
F 3 "~" H 4100 7300 50  0001 C CNN
F 4 "Optional, Bluetooth LED header" V 4100 7300 50  0001 C CNN "Comment"
	1    4100 7300
	0    1    1    0   
$EndComp
Wire Wire Line
	4000 5700 3900 5700
Wire Wire Line
	3900 5700 3900 5550
Connection ~ 3900 5550
Wire Wire Line
	4000 6400 3900 6400
Wire Wire Line
	3900 6400 3900 6250
Connection ~ 3900 6250
Wire Wire Line
	4100 6400 4200 6400
Wire Wire Line
	4200 6400 4200 6250
Connection ~ 4200 6250
Wire Wire Line
	4100 5700 4200 5700
Wire Wire Line
	4200 5700 4200 5550
Connection ~ 4200 5550
Wire Wire Line
	4100 7100 4200 7100
Wire Wire Line
	4200 7100 4200 6950
Connection ~ 4200 6950
Wire Wire Line
	4000 7100 3900 7100
Wire Wire Line
	3900 7100 3900 6950
Connection ~ 3900 6950
$Comp
L Device:R R16
U 1 1 604854F7
P 10450 1100
F 0 "R16" H 10380 1054 50  0000 R CNN
F 1 "4.7K" H 10380 1145 50  0000 R CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal" V 10380 1100 50  0001 C CNN
F 3 "~" H 10450 1100 50  0001 C CNN
	1    10450 1100
	-1   0    0    1   
$EndComp
Text GLabel 10450 1250 3    50   Input ~ 0
SIO_DATAIN
$Comp
L power:+5V #PWR0143
U 1 1 60485ABD
P 10450 950
F 0 "#PWR0143" H 10450 800 50  0001 C CNN
F 1 "+5V" H 10465 1123 50  0000 C CNN
F 2 "" H 10450 950 50  0001 C CNN
F 3 "" H 10450 950 50  0001 C CNN
	1    10450 950 
	1    0    0    -1  
$EndComp
$Comp
L power:+3.3V #PWR0110
U 1 1 604CBC19
P 9900 4800
F 0 "#PWR0110" H 9900 4650 50  0001 C CNN
F 1 "+3.3V" H 9915 4973 50  0000 C CNN
F 2 "" H 9900 4800 50  0001 C CNN
F 3 "" H 9900 4800 50  0001 C CNN
	1    9900 4800
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR0111
U 1 1 604CC6BE
P 9900 6000
F 0 "#PWR0111" H 9900 5750 50  0001 C CNN
F 1 "GND" H 9905 5827 50  0000 C CNN
F 2 "" H 9900 6000 50  0001 C CNN
F 3 "" H 9900 6000 50  0001 C CNN
	1    9900 6000
	1    0    0    -1  
$EndComp
Wire Wire Line
	9900 5900 9900 6000
Connection ~ 9900 6000
Wire Wire Line
	7850 5700 8950 5700
Wire Wire Line
	7850 5400 8050 5400
Wire Wire Line
	7850 5300 8650 5300
Wire Wire Line
	7850 5100 8350 5100
Wire Wire Line
	8950 4800 8950 5700
Connection ~ 8950 5700
Wire Wire Line
	8950 5700 9900 5700
Wire Wire Line
	8650 4800 8650 5300
Connection ~ 8650 5300
Wire Wire Line
	8650 5300 9900 5300
Wire Wire Line
	8350 4800 8350 5100
Connection ~ 8350 5100
Wire Wire Line
	8350 5100 9900 5100
Wire Wire Line
	8050 4800 8050 5400
Connection ~ 8050 5400
Wire Wire Line
	8050 5400 9900 5400
$Comp
L Device:CP1 C4
U 1 1 605422F3
P 8650 3550
F 0 "C4" H 8765 3596 50  0000 L CNN
F 1 "10uF 10V" H 8765 3505 50  0000 L CNN
F 2 "Capacitor_THT:CP_Radial_Tantal_D5.5mm_P5.00mm" H 8650 3550 50  0001 C CNN
F 3 "~" H 8650 3550 50  0001 C CNN
F 4 "Optional, 3.3V bulk for SD card" H 8650 3550 50  0001 C CNN "Comment"
	1    8650 3550
	1    0    0    -1  
$EndComp
$Comp
L power:+3.3V #PWR0112
U 1 1 60542995
P 8650 3400
F 0 "#PWR0112" H 8650 3250 50  0001 C CNN
F 1 "+3.3V" V 8665 3528 50  0000 L CNN
F 2 "" H 8650 3400 50  0001 C CNN
F 3 "" H 8650 3400 50  0001 C CNN
	1    8650 3400
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR0116
U 1 1 60542E6F
P 8650 3700
F 0 "#PWR0116" H 8650 3450 50  0001 C CNN
F 1 "GND" H 8655 3527 50  0000 C CNN
F 2 "" H 8650 3700 50  0001 C CNN
F 3 "" H 8650 3700 50  0001 C CNN
	1    8650 3700
	1    0    0    -1  
$EndComp
$Comp
L Switch:SW_MEC_5E SW1
U 1 1 6025CB40
P 5950 4100
F 0 "SW1" H 5950 4485 50  0000 C CNN
F 1 "BUTTON A" H 5950 4394 50  0000 C CNN
F 2 "Button_Switch_THT:SW_TH_Tactile_Omron_B3F-10xx" H 5950 4400 50  0001 C CNN
F 3 "http://www.apem.com/int/index.php?controller=attachment&id_attachment=1371" H 5950 4400 50  0001 C CNN
	1    5950 4100
	1    0    0    -1  
$EndComp
Wire Wire Line
	6150 4000 6000 4000
Wire Wire Line
	6000 4000 6000 4100
Connection ~ 6150 4000
Wire Wire Line
	5750 4000 5900 4000
Wire Wire Line
	5900 4000 5900 4100
Wire Wire Line
	6150 4700 6000 4700
Wire Wire Line
	6000 4700 6000 4800
Connection ~ 6150 4700
Wire Wire Line
	5750 4700 5900 4700
Wire Wire Line
	5900 4700 5900 4800
Wire Wire Line
	6150 5450 6000 5450
Wire Wire Line
	6000 5450 6000 5550
Connection ~ 6150 5450
Wire Wire Line
	5750 5450 5900 5450
Wire Wire Line
	5900 5450 5900 5550
$Comp
L power:GND #PWR0117
U 1 1 6071FB44
P 2250 1150
F 0 "#PWR0117" H 2250 900 50  0001 C CNN
F 1 "GND" V 2255 1022 50  0000 R CNN
F 2 "" H 2250 1150 50  0001 C CNN
F 3 "" H 2250 1150 50  0001 C CNN
	1    2250 1150
	0    1    1    0   
$EndComp
$Comp
L power:GND #PWR0137
U 1 1 60720F63
P 2250 1500
F 0 "#PWR0137" H 2250 1250 50  0001 C CNN
F 1 "GND" V 2255 1372 50  0000 R CNN
F 2 "" H 2250 1500 50  0001 C CNN
F 3 "" H 2250 1500 50  0001 C CNN
	1    2250 1500
	0    1    1    0   
$EndComp
$Comp
L power:GND #PWR0138
U 1 1 60721269
P 2250 1850
F 0 "#PWR0138" H 2250 1600 50  0001 C CNN
F 1 "GND" V 2255 1722 50  0000 R CNN
F 2 "" H 2250 1850 50  0001 C CNN
F 3 "" H 2250 1850 50  0001 C CNN
	1    2250 1850
	0    1    1    0   
$EndComp
$Comp
L power:GND #PWR0144
U 1 1 60721585
P 2250 2900
F 0 "#PWR0144" H 2250 2650 50  0001 C CNN
F 1 "GND" V 2255 2772 50  0000 R CNN
F 2 "" H 2250 2900 50  0001 C CNN
F 3 "" H 2250 2900 50  0001 C CNN
	1    2250 2900
	0    1    1    0   
$EndComp
$Comp
L power:GND #PWR0145
U 1 1 60721B65
P 3900 1150
F 0 "#PWR0145" H 3900 900 50  0001 C CNN
F 1 "GND" V 3905 1022 50  0000 R CNN
F 2 "" H 3900 1150 50  0001 C CNN
F 3 "" H 3900 1150 50  0001 C CNN
	1    3900 1150
	0    1    1    0   
$EndComp
$Comp
L Connector:DB15_Female_MountingHoles J10
U 1 1 6077F320
P 1650 3600
F 0 "J10" H 1805 3602 50  0000 L CNN
F 1 "DB15_Female_MountingHoles" H 1805 3511 50  0000 L CNN
F 2 "Connector_Dsub:DSUB-15_Female_Horizontal_P2.77x2.84mm_EdgePinOffset4.94mm_Housed_MountingHolesOffset7.48mm" H 1650 3600 50  0001 C CNN
F 3 " ~" H 1650 3600 50  0001 C CNN
F 4 "Do not connect Pin 12 in cable" H 1650 3600 50  0001 C CNN "Comment"
	1    1650 3600
	1    0    0    -1  
$EndComp
Text GLabel 1350 2900 0    50   Input ~ 0
SIO_CKIN
Text GLabel 1350 3100 0    50   Input ~ 0
SIO_CKOUT
Text GLabel 1350 3300 0    50   Input ~ 0
SIO_DATAIN
Text GLabel 1350 3700 0    50   Input ~ 0
SIO_DATAOUT
Text GLabel 1350 4100 0    50   Input ~ 0
SIO_CMD
Text GLabel 1350 4300 0    50   Input ~ 0
SIO_MCTL
Text GLabel 1350 3000 0    50   Input ~ 0
SIO_PROC
Text GLabel 1350 3400 0    50   Input ~ 0
SIO_AUDIOIN
Text GLabel 1350 3800 0    50   Input ~ 0
SIO_INT
$Comp
L power:GND #PWR0104
U 1 1 6079F6ED
P 1350 3500
F 0 "#PWR0104" H 1350 3250 50  0001 C CNN
F 1 "GND" V 1355 3372 50  0000 R CNN
F 2 "" H 1350 3500 50  0001 C CNN
F 3 "" H 1350 3500 50  0001 C CNN
	1    1350 3500
	0    1    1    0   
$EndComp
$Comp
L power:GND #PWR0146
U 1 1 607A0ECA
P 1350 3900
F 0 "#PWR0146" H 1350 3650 50  0001 C CNN
F 1 "GND" V 1355 3772 50  0000 R CNN
F 2 "" H 1350 3900 50  0001 C CNN
F 3 "" H 1350 3900 50  0001 C CNN
	1    1350 3900
	0    1    1    0   
$EndComp
$Comp
L 74xx:SN74LS07N U4
U 7 1 602A917D
P 4050 3800
F 0 "U4" H 4280 3846 50  0000 L CNN
F 1 "SN74LS07N" H 4280 3755 50  0000 L CNN
F 2 "Package_DIP:DIP-14_W7.62mm_Socket_LongPads" H 4050 3800 50  0001 C CNN
F 3 "www.ti.com/lit/ds/symlink/sn74ls07.pdf" H 4050 3800 50  0001 C CNN
	7    4050 3800
	1    0    0    -1  
$EndComp
$Comp
L 74xx:SN74LS07N U3
U 7 1 6024669D
P 3150 3800
F 0 "U3" H 3380 3846 50  0000 L CNN
F 1 "SN74LS07N" H 3380 3755 50  0000 L CNN
F 2 "Package_DIP:DIP-14_W7.62mm_Socket_LongPads" H 3150 3800 50  0001 C CNN
F 3 "www.ti.com/lit/ds/symlink/sn74ls07.pdf" H 3150 3800 50  0001 C CNN
	7    3150 3800
	1    0    0    -1  
$EndComp
$Comp
L Diode:1N5817 D4
U 1 1 607B0171
P 1650 5150
F 0 "D4" H 1650 4933 50  0000 C CNN
F 1 "1N5817" H 1650 5024 50  0000 C CNN
F 2 "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal" H 1650 4975 50  0001 C CNN
F 3 "http://www.vishay.com/docs/88525/1n5817.pdf" H 1650 5150 50  0001 C CNN
F 4 "1N5818 or 1N5819 also works" H 1650 5150 50  0001 C CNN "Comment"
	1    1650 5150
	-1   0    0    1   
$EndComp
$Comp
L power:+5V #PWR0148
U 1 1 607B20D4
P 1800 5150
F 0 "#PWR0148" H 1800 5000 50  0001 C CNN
F 1 "+5V" V 1815 5278 50  0000 L CNN
F 2 "" H 1800 5150 50  0001 C CNN
F 3 "" H 1800 5150 50  0001 C CNN
	1    1800 5150
	0    1    1    0   
$EndComp
Text GLabel 1500 5150 0    50   Input ~ 0
SIO_5V
Text GLabel 1350 3200 0    50   Input ~ 0
SIO_5V
Text GLabel 1150 1300 2    50   Input ~ 0
SIO_5V
$Comp
L Device:CP1 C5
U 1 1 607C61F7
P 1750 5950
F 0 "C5" V 2002 5950 50  0000 C CNN
F 1 "10uf 6.3V" V 1911 5950 50  0000 C CNN
F 2 "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm" H 1750 5950 50  0001 C CNN
F 3 "~" H 1750 5950 50  0001 C CNN
F 4 "Optional, 5V bulk for board" V 1750 5950 50  0001 C CNN "Comment"
	1    1750 5950
	1    0    0    -1  
$EndComp
$Comp
L power:+5V #PWR0149
U 1 1 607C729C
P 1750 5800
F 0 "#PWR0149" H 1750 5650 50  0001 C CNN
F 1 "+5V" H 1765 5973 50  0000 C CNN
F 2 "" H 1750 5800 50  0001 C CNN
F 3 "" H 1750 5800 50  0001 C CNN
	1    1750 5800
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR0150
U 1 1 607C761E
P 1750 6100
F 0 "#PWR0150" H 1750 5850 50  0001 C CNN
F 1 "GND" H 1755 5927 50  0000 C CNN
F 2 "" H 1750 6100 50  0001 C CNN
F 3 "" H 1750 6100 50  0001 C CNN
	1    1750 6100
	1    0    0    -1  
$EndComp
$Comp
L Graphic:Logo_Open_Hardware_Small #LOGO1
U 1 1 609D3971
P 850 7500
F 0 "#LOGO1" H 850 7775 50  0001 C CNN
F 1 "Logo_Open_Hardware_Small" H 850 7275 50  0001 C CNN
F 2 "Symbol:OSHW-Logo2_7.3x6mm_SilkScreen" H 850 7500 50  0001 C CNN
F 3 "~" H 850 7500 50  0001 C CNN
	1    850  7500
	1    0    0    -1  
$EndComp
NoConn ~ 1650 4500
$EndSCHEMATC
