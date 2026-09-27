// Fujiversal-Atari2600 Rev0 cartridge shell (parametric, two-piece clamshell)
// ---------------------------------------------------------------------------
// The bare board is the cartridge: its 32.4 mm tab and 45-degree shoulders go
// into the 2600's slot exactly as the FujiPlusCart prototype board did, so the
// shell covers ONLY the full-width part of the board above the shoulders and
// leaves the tab + shoulders bare.
//
// Coordinate frame = the KiCad board frame, so the generated anchors drop
// straight in:  X = board x (mm),  Y = -(board y)  (board y grows toward the
// contact edge; here +Y points up, away from the console),
//               Z = 0 at the outside of the FRONT half.
// FRONT half = the console-front face (B.Cu, label side, no parts).
// REAR  half = the component face (F.Cu), toward the console rear.
//
//   VERIFY on a console before printing a batch:
//   * slot_clear: the shell's bottom face sits this far above the contact
//     edge.  The prototype board carried parts from ~27.5 mm up and seated
//     fully; this shell stops at ~25.3 mm.  If the shell meets the console's
//     top before the fingers seat, raise bottom_y (and keep parts above it
//     in tools/placement.py).
//   * rear_h: tallest part on the component face is the ESP32-S3 module /
//     USB-C (~3.2 mm); 4.2 mm leaves room for the buttons' actuators to sit
//     just under the roof (press through the holes).
//
// Print: both halves face-down (outside on the bed), no supports; 0.2 mm
// layers.  Fasten with 4x M3x10 pan-head screws from the front into the
// rear bosses (M3 heat-set inserts, or self-tapping into the 2.6 mm pilots).

include <board-anchors.scad>

// ------------------------------------------------------------ parameters --
wall     = 1.6;     // side walls, front plate, rear roof
clr      = 0.3;     // board-to-wall clearance
pcb_t    = 1.6;
front_gap = 1.2;    // front plate inner face -> board B.Cu (solder, via tents)
rear_h   = 4.2;     // board F.Cu -> rear roof inner face (part height)
ant_over = 6.4;     // ESP32-S3 antenna overhang past the board's top edge
ant_x    = [ant[0] - 9.75, ant[0] + 9.75];   // module width (courtyard)
bottom_y = 90.9;    // shell's inner bottom (board y): below every part/boss
boss_rear_d = 4.6;  // rear bosses (must clear the parts round each hole)
boss_front_d = 6.0;
screw_d  = 3.4;     // clearance hole in the front half
pilot_d  = 2.6;     // rear pilot (self-tap); 4.0 for heat-set inserts
head_d   = 6.2;     // pan head counterbore in the front plate
head_h   = 1.0;

$fn = 40;
eps = 0.01;

x0 = board[0]; y0 = board[1]; x1 = board[2];
z_b  = wall + front_gap;          // board B.Cu face
z_f  = z_b + pcb_t;               // board F.Cu face
z_top = z_f + rear_h + wall;      // outside of the rear roof
slot_clear = board[3] - (bottom_y + wall);
echo(str("shell: ", x1 - x0 + 2 * (wall + clr), " x ", bottom_y - y0 + ant_over + 2 * wall,
         " x ", z_top, " mm; bottom face ", slot_clear, " mm above the contact edge"));

function Y(y) = -y;               // board y -> shell Y

// ---------------------------------------------------------------- outline --
// inner outline of the cavity (2D, shell frame): the board plus clearance,
// plus the antenna pocket over the top edge
module inner2d() {
    translate([x0 - clr, Y(bottom_y)]) square([x1 - x0 + 2 * clr, bottom_y - y0 + clr]);
    translate([ant_x[0] - clr, Y(y0) - eps]) square([ant_x[1] - ant_x[0] + 2 * clr, ant_over + clr]);
}
module outer2d() { offset(r = wall) inner2d(); }

// -------------------------------------------------------------- features --
module screw_holes() {
    for (h = holes) translate([h[0], Y(h[1])]) children();
}

// USB-C mouth and microSD slot at the top edge (y0), through the top wall
module top_cutouts() {
    // USB-C: receptacle 8.9 x 3.2 centred ~1.6 mm above F.Cu; opening sized
    // for a plug overmold (12.5 x 7) to seat
    translate([usb_x - 6.5, Y(y0) - eps, z_f - 1.8]) cube([13, wall + 2 * clr + 2 * eps, 7.2]);
    // microSD: card 11 x 0.8 enters just above F.Cu; slot + a finger notch
    translate([sd_x - 6.5, Y(y0) - eps, z_f - 0.2]) cube([13, wall + 2 * clr + 2 * eps, 2.4]);
    translate([sd_x, Y(y0) + wall + clr, z_top]) rotate([90, 0, 0]) cylinder(d = 10, h = wall + 2 * clr + 1);
}

// through the rear roof: buttons (RESET big, the rest pin-holes), light pipes
module roof_holes() {
    for (p = [[sw_reset, 5.0], [sw_bootsel, 2.2], [sw_s3rst, 2.2], [sw_s3boot, 2.2],
              [ws_led, 3.0], [rp_led, 2.0]])
        translate([p[0][0], Y(p[0][1]), z_top - wall - eps]) cylinder(d = p[1], h = wall + 2 * eps);
}

// ------------------------------------------------------------------ parts --
module front_half() {
    difference() {
        union() {
            linear_extrude(wall) outer2d();                       // front plate
            // perimeter rim up to the board's B face (the parting plane)
            linear_extrude(z_b) difference() { outer2d(); inner2d(); }
            screw_holes() cylinder(d = boss_front_d, h = z_b);    // board rests on these
            // antenna rest: fills under the overhanging module up to F.Cu level
            translate([ant_x[0], Y(y0), wall - eps]) cube([ant_x[1] - ant_x[0], ant_over - 0.2, z_f - wall]);
        }
        screw_holes() translate([0, 0, -eps]) cylinder(d = screw_d, h = z_b + 2 * eps);
        screw_holes() translate([0, 0, -eps]) cylinder(d = head_d, h = head_h + eps);
        // label recess on the outside
        translate([(x0 + x1) / 2 - 22, Y(bottom_y) + 8, -eps]) cube([44, 36, 0.4]);
    }
}

module rear_half() {
    difference() {
        union() {
            // side walls from the parting plane to the roof
            translate([0, 0, z_b]) linear_extrude(z_top - z_b) difference() { outer2d(); inner2d(); }
            translate([0, 0, z_top - wall]) linear_extrude(wall) outer2d();       // roof
            screw_holes() translate([0, 0, z_f]) cylinder(d = boss_rear_d, h = z_top - z_f);
        }
        screw_holes() translate([0, 0, z_f - eps]) cylinder(d = pilot_d, h = z_top - z_f - 0.6);
        // the board leaves through the bottom wall
        translate([x0 - clr, Y(bottom_y) - wall - eps, z_b - eps]) cube([x1 - x0 + 2 * clr, wall + 2 * eps, pcb_t + clr]);
        top_cutouts();
        roof_holes();
    }
}

// ---------------------------------------------------------------- output --
part = "both";   // "front", "rear", "both" (print layout), "assembled"
if (part == "front") front_half();
else if (part == "rear") translate([0, 0, z_top]) mirror([0, 0, 1]) rear_half();
else if (part == "assembled") { front_half(); rear_half(); }
else {
    front_half();
    translate([70, 0, z_top]) mirror([0, 0, 1]) rear_half();
}
