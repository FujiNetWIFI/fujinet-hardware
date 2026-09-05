// FujiNet-Astrocade Rev0 cartridge shell (parametric, two-piece)
// ---------------------------------------------------------------
// Coordinate frame:  X = cart width (0 = center),
//                    Y = depth, 0 = LEADING face (console blade enters here),
//                    Z = 0 at outside bottom.
//
// The Bally Astrocade "Videocade" is a closed cassette-style cart. The
// console mouth takes only the leading ~20 mm of the cart; the console
// blade (a single-row 26-contact wafer, ~74 mm wide, ~3.6-3.8 mm thick,
// reaching ~17 mm in) enters a slot in the leading face and presses UP
// against the gold lands on the PCB UNDERSIDE. The rest of the cart sits
// in an open-top well, so the rear body may be taller than an original
// cart, which is what lets USB-C / microSD clear the well rim.
//
// Every dimension marked VERIFY below came from photogrammetry against
// the cartreader-adapter gerbers (known 100.45 mm PCB in the same photo)
// or from the MCM Design cassette-mod document, not from a caliper.
// Measure a real Videocade + console before ordering plastics:
//   VERIFY cart_w / lead_d   (original cart ~102 x 65 mm measured +/-2)
//   VERIFY lead_h            (original cart thickness, ~12.5 mm)
//   VERIFY slot_w / slot_h   (blade ~74 wide; 3.6-3.8 thick works per
//                             sakman55's adapter: 1.2 PCB + 2.4-2.6 shims)
//   VERIFY blade_reach       (~17-18 mm insertion)
//   VERIFY well rim height   (drives body_h; 17 mm assumed safe)

// ------------------------------------------------------------ parameters --
cart_w     = 102;    // VERIFY  overall width
cart_d     = 65;     // VERIFY  overall depth (leading -> trailing)
lead_h     = 12.5;   // VERIFY  height of leading section (mouth-limited)
lead_d     = 22;     // depth of the reduced-height leading section
body_h     = 17;     // rear body height (open well above -> unconstrained)
wall       = 1.8;    // perimeter walls
floor_t    = 1.6;    // bottom shell floor
roof_t     = 1.6;    // top shell roof

slot_w     = 76;     // VERIFY  blade opening width (blade cut to 74 fits)
slot_h     = 4.2;    // VERIFY  blade opening height above inner floor
pcb_seat_z = floor_t + 4.0;  // underside of PCB: leaves blade + spring room

pcb_w      = 96;     // matches FujiNet-Astrocade-Rev0.kicad_pcb outline
pcb_d      = 58;
pcb_t      = 1.6;
pcb_lead_setback = 2.0;   // PCB leading edge sits this far behind cart face

split_z    = 9.0;    // bottom/top shell parting plane

$fn = 32;
eps = 0.01;

// Board(KiCad) -> cart transforms.  Board x52..148 centered on cart X=0;
// board y88 = leading edge of PCB.
function bx(x) = x - 100;
function byy(y) = (88 - y) + pcb_lead_setback;

// component anchors (from FujiNet-Astrocade-Rev0.kicad_pcb)
sw1   = [bx(141), byy(54)];    // RESET  (top-face button hole)
sw2   = [bx(141), byy(62)];    // BOOTSEL (pinhole)
ws    = [bx(100), byy(50.5)];  // WS2812 light pipe
usb   = [bx(124), byy(30)];    // USB-C exits trailing edge (board y30)
sd    = [bx(67),  byy(30)];    // microSD exits trailing edge
holes = [[bx(55), byy(33)], [bx(145), byy(33)], [bx(55), byy(84)], [bx(145), byy(84)]];
ant_c = bx(88);                // ESP32 antenna center X (overhangs trailing edge)

// outer envelope: low leading section + taller rear body, rounded corners
module envelope(h_lead, h_body) {
    translate([-cart_w/2, 0, 0]) cube([cart_w, lead_d, h_lead]);
    translate([-cart_w/2, lead_d, 0]) cube([cart_w, cart_d - lead_d, h_body]);
    // ramp between the two heights
    hull() {
        translate([-cart_w/2, lead_d - 6, 0]) cube([cart_w, eps, h_lead]);
        translate([-cart_w/2, lead_d, 0]) cube([cart_w, eps, h_body]);
    }
}

module cavity() {
    translate([-cart_w/2 + wall, wall, floor_t])
        linear_extrude(body_h) offset(1) offset(-1)
            square([cart_w - 2*wall, cart_d - 2*wall]);
}

module blade_slot() {
    // through the leading wall, open down to the inner floor level
    translate([-slot_w/2, -eps, floor_t])
        cube([slot_w, wall + 2, slot_h]);
    // interior blade channel up to the PCB underside
    translate([-slot_w/2, -eps, floor_t])
        cube([slot_w, wall + 20, pcb_seat_z - floor_t]);
}

module post(p, h, od=6, id=2.8) {
    translate([p[0], p[1], 0]) difference() {
        cylinder(d=od, h=h);
        translate([0, 0, -eps]) cylinder(d=id, h=h + 2*eps);
    }
}

// ------------------------------------------------------------ bottom half --
module bottom_shell() {
    difference() {
        intersection() {
            envelope(lead_h, body_h);
            translate([-200, -200, 0]) cube([400, 400, split_z]);
        }
        cavity();
        blade_slot();
        // screw clearance from below (countersunk M3)
        for (p = holes) translate([p[0], p[1], -eps]) {
            cylinder(d=3.4, h=floor_t + 2*eps);
            cylinder(d1=6.2, d2=3.4, h=1.2);
        }
    }
    // PCB support posts (PCB underside rests at pcb_seat_z)
    for (p = holes) post(p, pcb_seat_z, od=7, id=3.4);
    // side ledges outside the blade channel keep the PCB seated flat
    for (sx = [-1, 1])
        translate([sx*(slot_w/2 + 2) - 2, wall, floor_t])
            cube([4, 16, pcb_seat_z - floor_t]);
}

// --------------------------------------------------------------- top half --
module top_shell() {
    pcb_top = pcb_seat_z + pcb_t;
    difference() {
        intersection() {
            envelope(lead_h, body_h);
            translate([-200, -200, split_z]) cube([400, 400, 200]);
        }
        cavity();
        // trailing-face port openings (sized generously; tune on print)
        translate([usb[0] - 5.2, cart_d - wall - eps, pcb_top - 0.4])
            cube([10.4, wall + 2, 4.4]);                    // USB-C
        translate([sd[0] - 8, cart_d - wall - eps, pcb_top - 0.4])
            cube([16, wall + 2, 3.4]);                      // microSD
        // top-face holes
        translate([sw1[0], sw1[1], -eps]) cylinder(d=4.5, h=200);   // RESET
        translate([sw2[0], sw2[1], -eps]) cylinder(d=2.0, h=200);   // BOOTSEL pin
        translate([ws[0], ws[1], -eps])   cylinder(d=2.5, h=200);   // LED pipe
        // label recess
        translate([-cart_w/2 + 8, lead_d + 6, body_h - 0.6])
            cube([cart_w - 16, cart_d - lead_d - 14, 1]);
        // ESP32 antenna window: module overhangs the PCB trailing edge by
        // ~6.4 mm; its tip sits ~1.4 mm proud of the trailing face. Open
        // window keeps the RF keepout plastic-free. VERIFY well clearance.
        translate([ant_c - 11, cart_d - wall - eps, pcb_seat_z + pcb_t - 0.5])
            cube([22, wall + 3, 8]);
    }
    // screw bosses meet the bottom posts at the PCB top face
    for (p = holes) difference() {
        translate([p[0], p[1], pcb_top])
            cylinder(d=7, h=(p[1] < lead_d ? lead_h : body_h) - roof_t - pcb_top);
        translate([p[0], p[1], pcb_top - eps]) cylinder(d=2.8, h=200);
    }
    // clamp ribs over the blade strip: press the PCB down against the
    // blade's contact springs (x chosen clear of top-side parts)
    for (rx = [-40, 40])
        translate([rx - 1.5, wall, pcb_top])
            cube([3, 14, lead_h - roof_t - pcb_top]);
}

// --------------------------------------------------------------- assembly --
// render selection: "bottom", "top", or "assembly"
part = "assembly";

if (part == "bottom") bottom_shell();
else if (part == "top") top_shell();
else {
    bottom_shell();
    color("steelblue", 0.5) translate([-pcb_w/2, pcb_lead_setback, pcb_seat_z])
        cube([pcb_w, pcb_d, pcb_t]);
    color("dimgray", 0.35) top_shell();
}
