// FujiNet-ColecoVision Rev0 cartridge shell (parametric, two-piece clamshell)
// ---------------------------------------------------------------------------
// The board is the ColecoVision cart outline, 40.2 x 82.4 mm, four side notches.  This shell has a
// reproduction shell's outside (82 x 97 x 19 mm: aotta's PiCOLECO shell, GPL-3.0, measured only, and
// sparkletron's 82.6 x 99 x 22.9) and holds the board the way PiCOLECO's does: the back face of the
// board 6.1 mm off the back, the board centred in the width, its fingers 12 mm inside the open skirt
// that takes the console's connector.  No original shell, cartridge or console was measured:
// case/case-spec.md has every number and its source, and the ones marked VERIFY are estimates.
// (FujiNet-O2 Rev0's shell, adapted.)
//
// Coordinate frame = the KiCad board frame, so the generated anchors drop in:
//   X = board x (mm),  Y = -(board y)  (+Y up, away from the console),
//   Z = 0 at the outside of the BACK half, Z grows toward the label face.
// FRONT half = over F.Cu: every part and the even pins; the label face (the component face of a
//              ColecoVision cart faces its label, sparkletron's manual).  It has RESET (a plunger),
//              the S3 BOOT and BOOTSEL pin-holes, the LED windows and a label recess.
// BACK  half = over B.Cu (the odd pins, no parts).  It has a label recess and the four screw heads.
// The halves meet at the board's B.Cu face.  Four M2.5 screws go in from the back half, through bosses
// beside the board (the board has no holes), into the front half's bosses.  The skirt (the shell
// below the fingers) is open: the console's cartridge connector enters it.
//
// Print: both halves outside-down, no supports, 0.2 mm layers, PETG (or PLA).  No carbon-fibre or
// metal-filled filament: the ESP32-S3's antenna is behind the west wall.
// Screws: 4x M2.5x12 pan head, self-tapping into the 2.1 mm pilots.

include <board-anchors.scad>

// ------------------------------------------------------------ parameters --
shell_w   = 82.0;   // outside width (PiCOLECO 82.0; sparkletron 82.55)
shell_h   = 97.0;   // outside length (PiCOLECO 97.0; sparkletron 99.06)
shell_d   = 19.0;   // outside thickness (PiCOLECO 19.0)
wall      = 2.0;    // walls and the front plate
back_t    = 2.5;    // back plate (PiCOLECO's floor)
z_b       = 6.1;    // board B.Cu face above the back's outside (PiCOLECO's ribs top out here)
top_clr   = 1.5;    // board top edge to the top wall: clear of the back half's lip
lip       = 1.0;    // back half's alignment lip (an inset rim up into the front half)
r_out     = 3.0;    // outer corner radius (plan view)
ledge_y   = 120.5;  // the back ledge and the front ribs stop here (board y): the console's connector
                    // body surrounds the fingers below this (VERIFY: the connector's depth)
rib_w     = 1.2;    // front side ribs and the back ledge reach this far onto the board
rib_y     = [[84.0, ledge_y], [87.4, ledge_y]];   // front side ribs, left / right (board y): below the
                    // module (left), below the buck, the buttons and the WS2812 (right)
key_clr   = 0.15;   // notch keys: clearance in the board's notches
key_up    = 1.0;    // ... rising this far above F.Cu into sockets in the front side ribs
boss_d    = 6.0;    // screw bosses beside the board
boss_xy   = [[64, 50], [136, 50], [64, 122], [136, 122]];   // board frame (x, y): clear of the board and
                    // 15 mm from the antenna strip; the lower two above the console's connector (VERIFY)
screw_d   = 2.9;    // M2.5 clearance through the back boss
pilot_d   = 2.1;    // front boss pilot for an M2.5 self-tapping screw
head_d    = 5.0;    // pan-head counterbore in the back plate
head_h    = 1.6;
label_t   = 0.4;    // label recess depth (0: none)
label_front   = [74, 22];   // front face: over the module, clear of the buttons and the LEDs
label_front_c = [100, 62.5];
label_back    = [56, 70];   // back face: between the screw heads
label_back_c  = [100, 88];
sw_h      = 1.5;    // TS-1187A above F.Cu (XKB drawing)
proud     = 0.6;    // RESET plunger's cap above the front face
press_gap = 0.15;   // RESET plunger's stem above the button at rest
pin_d     = 2.2;    // pin-holes for S3 BOOT and BOOTSEL (a straightened paper clip)
led_win   = [[led_status, 3.0, true], [led_rp, 2.0, false]];   // LED windows: WS2812 (shrouded), the RP's red LED
                    // (no shroud: it would reach the ESP32-S3 module beside it)

$fn = 48;
eps = 0.01;

// ---------------------------------------------------------- derived frame --
z_f     = z_b + pcb_t;               // board F.Cu face
z_fin   = shell_d - wall;            // front plate's inner face
gap_b   = z_b - back_t;              // back plate to B.Cu
gap_f   = z_fin - z_f;               // F.Cu to the front plate
xc      = (pcb_x0 + pcb_x1) / 2;
sx0     = xc - shell_w / 2;  sx1 = xc + shell_w / 2;
y_top   = pcb_y0 - top_clr - wall;   // shell top (board y)
y_bot   = y_top + shell_h;           // shell bottom: the skirt's open end (board y)
skirt   = y_bot - pcb_y1;            // shell beyond the fingers
y_in_top = y_top + wall;             // top wall's inner face (board y)
// RESET plunger (FujiNet-O2 Rev0's)
guide_od = 8.6;  guide_id = 6.4;  guide_h = 2.6;
cap_d   = 4.4;  cap_hole = 4.8;  fl_d = 6.0;  stem_d = 2.6;
tube_od = pin_d + 2.2;               // pin-hole guide tubes
tube_z  = z_f + sw_h + 1.0;          // ... ending 1 mm above the buttons
shroud_z = z_f + 2.0;                // LED shrouds end 2 mm above F.Cu
pilot_top = shell_d - 1.4;           // the pilot stops 1.4 mm short of the front face

function Y(y) = -y;                  // board y -> shell Y
function d2(a, b) = norm([a[0] - b[0], a[1] - b[1]]);
function inside(p, c, wh, m) = abs(p[0] - c[0]) < wh[0] / 2 + m && abs(p[1] - c[1]) < wh[1] / 2 + m;
function boxes_meet(a, b) = a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
function box_dist(p, b) = norm([max(b[0] - p[0], 0, p[0] - b[2]), max(b[1] - p[1], 0, p[1] - b[3])]);

face_holes = concat([[sw_reset, cap_hole], [sw_bootsel, tube_od], [sw_s3boot, pin_d]],
                    [for (l = led_win) [l[0], l[1] + 1.6]]);    // [centre, outer diameter]
rib_boxes = [[pcb_x0 - 1, rib_y[0][0], pcb_x0 + rib_w, rib_y[0][1]], [pcb_x1 - rib_w, rib_y[1][0], pcb_x1 + 1, rib_y[1][1]]];
bosses_box = [for (b = boss_xy) [b[0] - boss_d / 2, b[1] - boss_d / 2, b[0] + boss_d / 2, b[1] + boss_d / 2]];

// the numbers the board and the console need, checked
assert(sx0 + wall + 1 <= pcb_x0 && pcb_x1 <= sx1 - wall - 1, "board wider than the cavity");
assert(gap_f >= parts_max_h + 0.8, "parts too tall for the front gap");
assert(gap_b >= 1.0, "no room for the back ledge");
assert(skirt >= 10, "the skirt is too short to take the console's connector");
assert(len([for (n = pcb_notches) if (n[3] + 1.0 > ledge_y) 1]) == 0, "a notch key in the connector's space");
assert(len([for (b = boss_xy) if (box_dist(b, ant_keep) < 15 + head_d / 2) 1]) == 0, "a screw within 15 mm of the antenna");
assert(len([for (b = bosses_box) if (boxes_meet(b, [pcb_x0 - 0.5, pcb_y0 - 0.5, pcb_x1 + 0.5, pcb_y1 + 0.5])) 1]) == 0, "a boss on the board");
assert(d2(sw_s3boot, sw_reset) >= guide_od / 2 + pin_d / 2 + 0.4 - 1e-6, "the RESET guide meets the S3 BOOT hole");
assert(len([for (f = face_holes) if (inside(f[0], label_front_c, label_front, f[1] / 2 + 1)) 1]) == 0, "a face hole in the front label");
assert(len([for (b = boss_xy) if (inside(b, label_back_c, label_back, head_d / 2 + 1)) 1]) == 0, "a screw head in the back label");
assert(len([for (r = rib_boxes, p = parts) if (boxes_meet(r, p)) 1]) == 0, "a side rib on a part");
echo(str("shell: ", shell_w, " x ", shell_h, " x ", shell_d, " mm (W x H x D); B.Cu at z ", z_b, ", F.Cu at z ", z_f,
         "; back gap ", gap_b, ", front gap ", gap_f, " (tallest part ", parts_max_h, "); skirt ", skirt,
         " mm beyond the fingers"));

// ---------------------------------------------------------------- outline --
module outer2d() {
    translate([sx0 + r_out, Y(y_bot) + r_out]) offset(r = r_out)
        square([shell_w - 2 * r_out, shell_h - 2 * r_out]);
}
module inner2d() { offset(delta = -wall) outer2d(); }
module lip2d()   { difference() { inner2d(); offset(delta = -wall - lip) outer2d(); } }
module board2d() { polygon([for (p = pcb_outline) [p[0], Y(p[1])]]); }
module at(p)     { translate([p[0], Y(p[1])]) children(); }
module bosses()  { for (b = boss_xy) at(b) children(); }
// the open end: the skirt has no bottom wall
module skirt_cut() { translate([sx0 + wall, Y(y_bot) - 1, back_t]) cube([shell_w - 2 * wall, wall + 1 + eps, z_fin - back_t]); }

// ------------------------------------------------------------ openings ---
// USB-C through the top wall (both halves): receptacle 8.94 x 3.26, its centre 1.63 above F.Cu; the
// opening takes a plug's overmold (up to 12.5 x 7), which stops at the receptacle's face 0.46 mm
// past the board edge.  The microSD's card (11 x 0.8) enters ~1 mm above F.Cu.
module top_openings() {
    translate([usb_c[0] - 6.5, Y(pcb_y0) - eps, z_f + 1.63 - 3.6]) cube([13, pcb_y0 - y_top + 2 * eps, 7.2]);
    translate([microsd[0] - 7, Y(pcb_y0) - eps, z_f + 0.2]) cube([14, pcb_y0 - y_top + 2 * eps, 2.4]);
}
// the front half's top wall open over the card, from the slot to the front face: the latched card's
// end is then in reach of a thumb, to push the push-push card home
module sd_notch() { translate([microsd[0] - 7, Y(pcb_y0) - eps, z_f + 0.2]) cube([14, pcb_y0 - y_top + 2 * eps, shell_d - z_f]); }

// front face: RESET through a plunger; S3 BOOT and BOOTSEL through pin-holes (BOOTSEL's in a guide tube); LED windows
module face_cuts() {
    at(sw_reset) {
        translate([0, 0, z_fin - eps]) cylinder(d = cap_hole, h = wall + 2 * eps);
        translate([0, 0, z_fin - guide_h - eps]) cylinder(d = guide_id, h = guide_h + eps);
    }
    at(sw_s3boot) translate([0, 0, z_fin - eps]) cylinder(d = pin_d, h = wall + 2 * eps);   // no tube: next to RESET's guide
    at(sw_bootsel) translate([0, 0, tube_z - eps]) cylinder(d = pin_d, h = shell_d - tube_z + 2 * eps);
    for (l = led_win) at(l[0]) translate([0, 0, (l[2] ? shroud_z : z_fin) - eps]) cylinder(d = l[1], h = shell_d - (l[2] ? shroud_z : z_fin) + 2 * eps);
}
module face_tubes() {
    at(sw_reset) translate([0, 0, z_fin - guide_h]) cylinder(d = guide_od, h = guide_h + eps);
    at(sw_bootsel) translate([0, 0, tube_z]) cylinder(d = tube_od, h = z_fin - tube_z + eps);
    for (l = led_win) if (l[2]) at(l[0]) translate([0, 0, shroud_z]) cylinder(d = l[1] + 1.6, h = z_fin - shroud_z + eps);
}

module label_recess(c, wh, z) {
    if (label_t > 0) translate([c[0] - wh[0] / 2, Y(c[1]) - wh[1] / 2, z]) cube([wh[0], wh[1], label_t + eps]);
}

// ---------------------------------------------------------- board holding --
// front: ribs on F.Cu along the sides' lower part (the parts reach the edges higher up)
module side_ribs() {
    for (r = rib_boxes)
        translate([r[0], Y(r[3]) - eps, z_f]) cube([r[2] - r[0], r[3] - r[1] + eps, z_fin - z_f + eps]);
}
// back: a ledge round the board's edge under B.Cu (B.Cu has no parts), above the connector's space
module ledge2d() {
    intersection() {
        difference() { inner2d(); offset(delta = -rib_w) board2d(); }
        translate([sx0, Y(ledge_y)]) square([shell_w, ledge_y - y_top]);
    }
}
// back: keys through the board's side notches, up into the front side ribs
module notch_keys(grow = 0, z0 = back_t - eps, z1 = z_f + key_up) {
    for (n = pcb_notches)
        translate([n[0] + key_clr - grow - (n[0] < xc ? 2 : 0), Y(n[3]) + key_clr - grow, z0])
            cube([n[2] - n[0] - 2 * key_clr + 2 * grow + 2, n[3] - n[1] - 2 * key_clr + 2 * grow, z1 - z0]);
}
module lip_seat() { translate([0, 0, z_b - eps]) linear_extrude(lip + 0.2) offset(delta = 0.15) lip2d(); }

// ------------------------------------------------------------------ parts --
module front_half() {
    difference() {
        union() {
            translate([0, 0, z_fin]) linear_extrude(wall) outer2d();                            // front plate
            translate([0, 0, z_b]) linear_extrude(shell_d - z_b) difference() { outer2d(); inner2d(); }
            side_ribs();
            bosses() translate([0, 0, z_b]) cylinder(d = boss_d, h = z_fin - z_b + eps);
            face_tubes();
        }
        bosses() translate([0, 0, z_b - eps]) cylinder(d = pilot_d, h = pilot_top - z_b + eps);
        notch_keys(grow = 0.2, z0 = z_b - eps, z1 = z_f + key_up + 0.3);                        // key sockets
        face_cuts();
        lip_seat();
        skirt_cut();
        top_openings();
        sd_notch();
        label_recess(label_front_c, label_front, shell_d - label_t);
    }
}

module back_half() {
    difference() {
        union() {
            linear_extrude(back_t) outer2d();                                                  // back plate
            linear_extrude(z_b) difference() { outer2d(); inner2d(); }                        // walls to the parting plane
            translate([0, 0, back_t - eps]) linear_extrude(gap_b + eps) ledge2d();             // B.Cu rests on the ledge
            bosses() cylinder(d = boss_d, h = z_b);                                            // the bosses
            translate([0, 0, z_b - eps]) linear_extrude(lip + eps) lip2d();                     // alignment lip
            intersection() { notch_keys(); linear_extrude(shell_d) inner2d(); }
        }
        bosses() {
            translate([0, 0, -eps]) cylinder(d = screw_d, h = z_b + 2 * eps);
            translate([0, 0, -eps]) cylinder(d = head_d, h = head_h + eps);
        }
        skirt_cut();
        top_openings();
        label_recess(label_back_c, label_back, -eps);
    }
}

// RESET plunger, modelled cap-down (its print orientation): the cap through the 4.8 mm hole, a 45-degree
// cone (no support) into a flange held in the guide, a stem onto the TS-1187A.  At rest the cone sits
// on the hole's edge, the cap `proud` above the face and the stem `press_gap` above the button.
cap_l    = wall + proud - (cap_hole - cap_d) / 2;
cone_h   = (fl_d - cap_d) / 2;
stem_end = wall + proud + gap_f - sw_h - press_gap;     // from the cap's top
module plunger() {
    cylinder(d = cap_d, h = cap_l + eps);
    translate([0, 0, cap_l]) cylinder(d1 = cap_d, d2 = fl_d, h = cone_h);
    translate([0, 0, cap_l + cone_h - eps]) cylinder(d = fl_d, h = 0.7 + eps);
    translate([0, 0, cap_l + cone_h + 0.7 - eps]) cylinder(d = stem_d, h = stem_end - (cap_l + cone_h + 0.7) + eps);
}
module plunger_fitted(drop = 0) {
    at(sw_reset) translate([0, 0, shell_d + proud - drop]) rotate([180, 0, 0]) plunger();
}

// the board and its parts, for the "assembled" / "section" / "check" views
module board(shrink = 0) {
    translate([0, 0, z_b + shrink]) linear_extrude(pcb_t - 2 * shrink) offset(delta = -shrink) board2d();
}
module part_boxes(lift = 0) {       // every F.Cu courtyard, extruded to its part's height
    for (p = parts) translate([p[0], Y(p[3]), z_f + 0.01 + lift]) cube([p[2] - p[0], p[3] - p[1], p[4]]);
}
module assembled() {
    color("khaki") back_half();
    color("khaki", 0.6) front_half();
    color("green") board();
    color("gray") part_boxes();
    color("red") plunger_fitted();
}

// print orientation: turned over (a rotation, never a mirror: mirroring gives the half's mirror image)
module front_print() {             // turned about its own middle, so it lands on the back half's footprint
    translate([0, Y(y_top) + Y(y_bot), shell_d]) rotate([180, 0, 0]) front_half();
}

// ---------------------------------------------------------------- output --
part = "both";   // "front", "back", "plunger", "both" (print layout), "assembled", "section", "check",
                 // "parts_check", "parts_control"
if (part == "front") front_print();
else if (part == "back") back_half();
else if (part == "plunger") plunger();
else if (part == "assembled") assembled();
else if (part == "section")      // cut across the RP, seen from the top
    difference() { assembled(); translate([sx0 - 1, Y(96), -1]) cube([shell_w + 2, shell_h, shell_d + 2]); }
else if (part == "check") {      // must be empty: the board and the plunger only touch the shell
    intersection() { board(0.05); front_half(); }
    intersection() { board(0.05); back_half(); }
    intersection() { plunger_fitted(0.05); front_half(); }
}
else if (part == "parts_check") {    // must be empty: every part's courtyard box, to its height, clears the shell
    intersection() { part_boxes(); front_half(); }
    intersection() { part_boxes(); back_half(); }
}
else if (part == "parts_control")    // must NOT be empty: the same boxes raised to the front plate meet it
    intersection() { part_boxes(gap_f - 1.0); front_half(); }
else {
    back_half();
    translate([shell_w + 12, 0, 0]) front_print();
    translate([sx1 + 6, Y(y_bot) + 8, 0]) plunger();
}
