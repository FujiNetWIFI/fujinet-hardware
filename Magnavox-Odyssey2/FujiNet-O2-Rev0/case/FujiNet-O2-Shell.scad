// FujiNet-O2 Rev0 cartridge shell (parametric, two-piece clamshell)
// ---------------------------------------------------------------------------
// The board is bwack's / PicoPAC's 63 x 85 mm Videopac outline.  This shell holds it the way those
// boards are meant to be held: two posts through the 5 mm holes, and keys in the side notches.  The
// bottom of the board stays bare, to enter the console's slot.  No original shell, cartridge or
// console was measured: case/case-spec.md has every number and its source, and the ones marked
// VERIFY there are estimates.  (FujiNet-StudioII Rev0's shell, adapted.)
//
// Coordinate frame = the KiCad board frame, so the generated anchors drop in:
//   X = board x (mm),  Y = -(board y)  (+Y up, away from the console),
//   Z = 0 at the outside of the BACK half, Z grows toward the player.
// FRONT half = over F.Cu: every part, and pins 1-15.  In a G7000 that face is toward the player
//              (PicoPAC's photos).  It has the buttons, the LED windows and a label recess.
// BACK  half = over B.Cu (pins A-R, no parts), toward the back of the console.  It has a label
//              recess and the two screw heads.
// The halves meet at the board's B.Cu face.  Two M2.5 screws go in from the back half, through the
// back bosses, into the front half's spigots, which pass through the board's holes.  Two snap hooks
// hold the top: the board has no holes up there, where the ESP32-S3's antenna is.
//
// Print: both halves outside-down, no supports, 0.2 mm layers, PETG (or PLA).  No carbon-fibre or
// metal-filled filament: the antenna is behind the top wall.
// Screws: 2x M2.5x10 pan head, self-tapping into the 2.1 mm pilots.

include <board-anchors.scad>

// ------------------------------------------------------------ parameters --
wall      = 2.0;    // walls and plates
lip       = 1.0;    // back half's alignment lip (an inset rim up into the front half)
clr       = 0.5;    // board edge to the lip
r_out     = 3.0;    // outer corner radius (plan view)
gap_b     = 3.0;    // back plate to B.Cu (no parts on B.Cu); sets the board's depth in the shell (VERIFY)
gap_f     = 5.0;    // F.Cu to the front plate: the 3.26 mm USB-C, the RESET plunger's guide
board_out = 17.0;   // bare board below the shell, entering the console (VERIFY: the slot's depth)
post_d    = 8.6;    // post collars and bosses (no part within 4.5 mm of a hole centre)
spig_d    = 4.6;    // front spigot through the board's 5.0 mm hole
spig_in   = 1.0;    // ... reaching this far into the back boss's socket (registers the halves)
screw_d   = 2.9;    // M2.5 clearance through the back boss
pilot_d   = 2.1;    // spigot pilot for an M2.5 self-tapping screw
head_d    = 5.0;    // pan-head counterbore in the back plate
head_h    = 1.6;
rib_w     = 1.2;    // front side ribs and the back ledge reach this far onto the board
rib_l     = [89.0, 85.0];   // the front side ribs start this far down (board y), left / right: below
                            // the BOOTSEL button (left) and the buck's capacitors (right)
key_clr   = 0.15;   // notch keys: clearance in the board's notches
key_up    = 1.0;    // ... rising this far above F.Cu into sockets in the front side ribs
hooks     = true;   // the two snap hooks at the top
hook_x    = [96, 122];  // their centres: clear of the USB-C opening; the right one is over the antenna (plastic)
hook_w    = 8.0;
hook_t    = 1.0;    // tongue thickness
hook_l    = 5.0;    // tongue height above the parting plane
barb      = 0.6;    // barb depth
label_t   = 0.4;    // label recess depth (0: none)
label_front   = [44, 14];   // front face: under the RP, clear of the buttons and the LEDs
label_front_c = [100, 104];
label_back    = [54, 46];   // back face: between the top and the screw heads
label_back_c  = [100, 72];
sw_h      = 1.5;    // TS-1187A above F.Cu (XKB drawing)
proud     = 0.6;    // RESET plunger's cap above the front face
press_gap = 0.15;   // RESET plunger's stem above the button at rest
pin_d     = 2.2;    // pin-holes for BOOTSEL, S3 EN, S3 BOOT (a straightened paper clip)
led_win   = [[led_status, 3.0], [led_rp, 2.0]];   // LED windows: WS2812, the RP's red LED

$fn = 48;
eps = 0.01;

// ---------------------------------------------------------- derived frame --
z_b     = wall + gap_b;              // board B.Cu face: the parting plane
z_f     = z_b + pcb_t;               // board F.Cu face
z_fin   = z_f + gap_f;               // front plate's inner face
shell_d = z_fin + wall;
xc      = (pcb_x0 + pcb_x1) / 2;
shell_w = pcb_x1 - pcb_x0 + 2 * (wall + lip + clr);
sx0     = xc - shell_w / 2;  sx1 = xc + shell_w / 2;
y_bot   = pcb_y1 - board_out;        // shell bottom (board y)
y_top   = pcb_y0 - clr - lip - wall; // shell top (board y)
shell_h = y_bot - y_top;
y_in_top = y_top + wall;             // top wall's inner face (board y)
y_in_bot = y_bot - wall;             // bottom wall's inner face
// RESET plunger, smaller than Studio II's: BOOTSEL is 6.4 mm away
guide_od = 8.6;  guide_id = 6.4;  guide_h = 2.6;
cap_d   = 4.4;  cap_hole = 4.8;  fl_d = 6.0;  stem_d = 2.6;
tube_od = pin_d + 2.2;               // pin-hole guide tubes (S3 EN, S3 BOOT)
tube_z  = z_f + sw_h + 1.0;          // ... ending 1 mm above the buttons
shroud_z = z_f + 2.0;                // LED shrouds end 2 mm above F.Cu
pilot_top = shell_d - 1.4;           // the pilot stops 1.4 mm short of the front face

function Y(y) = -y;                  // board y -> shell Y
function d2(a, b) = norm([a[0] - b[0], a[1] - b[1]]);
function inside(p, c, wh, m) = abs(p[0] - c[0]) < wh[0] / 2 + m && abs(p[1] - c[1]) < wh[1] / 2 + m;
function boxes_meet(a, b) = a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];

face_holes = concat([[sw_reset, cap_hole], [sw_bootsel, pin_d], [sw_s3en, tube_od], [sw_s3boot, tube_od]],
                    [for (l = led_win) [l[0], l[1] + 1.6]]);    // [centre, outer diameter]
rib_boxes = [[pcb_x0 - 1, rib_l[0], pcb_x0 + rib_w, y_in_bot], [pcb_x1 - rib_w, rib_l[1], pcb_x1 + 1, y_in_bot]];

// the numbers the board and the console need, checked
assert(sx0 + wall + lip + clr <= pcb_x0 + 1e-6 && pcb_x1 <= sx1 - wall - lip - clr + 1e-6, "board wider than the cavity");
assert(gap_f >= parts_max_h + 0.8, "parts too tall for the front gap");
assert(y_in_bot >= parts_min_y, "the bottom wall would sit on parts");
assert(y_bot <= contacts_y - 2, "the shell would cover the contacts");
assert(len([for (n = pcb_notches) if (n[3] + 1.0 > y_in_bot) 1]) == 0, "a notch key outside the shell");
assert(len([for (h = pcb_holes) if (d2(h, esp32_ant) < 15 + head_d / 2) 1]) == 0, "a screw within 15 mm of the antenna");
assert(d2(sw_bootsel, sw_reset) >= guide_od / 2 + pin_d / 2 + 0.4, "the RESET guide meets the BOOTSEL hole");
assert(d2(sw_s3en, sw_s3boot) >= tube_od + 0.4, "the S3 pin-hole tubes meet");
assert(len([for (f = face_holes) if (inside(f[0], label_front_c, label_front, f[1] / 2 + 1)) 1]) == 0, "a face hole in the front label");
assert(len([for (h = pcb_holes) if (inside(h, label_back_c, label_back, head_d / 2 + 1)) 1]) == 0, "a screw head in the back label");
assert(len([for (hx = hook_x) if (abs(hx - usb_c[0]) < hook_w / 2 + 7.5) 1]) == 0, "a hook in the USB-C opening");
assert(len([for (r = rib_boxes, p = parts) if (boxes_meet(r, p)) 1]) == 0, "a side rib on a part");
assert(post_d / 2 <= post_keep, "a post collar wider than the parts-free ring");
echo(str("shell: ", shell_w, " x ", shell_h, " x ", shell_d, " mm (W x H x D); B.Cu at z ", z_b, ", F.Cu at z ", z_f,
         "; back gap ", gap_b, ", front gap ", gap_f, " (tallest part ", parts_max_h, "); ", board_out,
         " mm of board below the shell"));

// ---------------------------------------------------------------- outline --
module outer2d() {
    translate([sx0 + r_out, Y(y_bot) + r_out]) offset(r = r_out)
        square([shell_w - 2 * r_out, shell_h - 2 * r_out]);
}
module inner2d() { offset(delta = -wall) outer2d(); }
module lip2d()   { difference() { inner2d(); offset(delta = -wall - lip) outer2d(); } }
module board2d() { polygon([for (p = pcb_outline) [p[0], Y(p[1])]]); }
module at(p)     { translate([p[0], Y(p[1])]) children(); }
module posts()   { for (h = pcb_holes) at(h) children(); }

// where the board leaves through the bottom wall (and the lip): the front half's bottom wall rests
// on F.Cu across the parts-free band
module board_slot() {
    translate([pcb_x0 - 0.3, Y(y_bot) - 1, z_b - eps])
        cube([pcb_x1 - pcb_x0 + 0.6, 1 + wall + lip + clr, z_f - z_b + eps]);
}

// ------------------------------------------------------------ openings ---
// USB-C through the top wall (both halves): receptacle 8.94 x 3.26, its centre 1.63 above F.Cu; the
// opening takes a plug's overmold (up to 12.5 x 7), which stops at the receptacle's face 0.46 mm
// past the board edge
module top_openings() {
    translate([usb_c[0] - 6.5, Y(pcb_y0) - eps, z_f + 1.63 - 3.6]) cube([13, pcb_y0 - y_top + 2 * eps, 7.2]);
}
// microSD through the left wall: the card (11 x 0.8) enters ~1 mm above F.Cu; latched, it stands
// 2.5 mm proud of the TF-015's face (0.5 mm inside the board edge)
module side_openings() {
    translate([sx0 - eps, Y(microsd[1]) - 7, z_f + 0.2]) cube([pcb_x0 - sx0 + 2 * eps, 14, 2.4]);
}
// the front half's left wall open over the card, from the slot to the front face: the latched card's
// end is then in reach of a thumb, to push the push-push card home
module sd_notch() { translate([sx0 - eps, Y(microsd[1]) - 7, z_f + 0.2]) cube([pcb_x0 - sx0 + 2 * eps, 14, shell_d - z_f]); }

// front face: RESET through a plunger; BOOTSEL, S3 EN, S3 BOOT through pin-holes; LED windows
module face_cuts() {
    at(sw_reset) {
        translate([0, 0, z_fin - eps]) cylinder(d = cap_hole, h = wall + 2 * eps);
        translate([0, 0, z_fin - guide_h - eps]) cylinder(d = guide_id, h = guide_h + eps);
    }
    at(sw_bootsel) translate([0, 0, z_fin - eps]) cylinder(d = pin_d, h = wall + 2 * eps);   // no tube: next to RESET's guide
    for (p = [sw_s3en, sw_s3boot]) at(p) translate([0, 0, tube_z - eps]) cylinder(d = pin_d, h = shell_d - tube_z + 2 * eps);
    for (l = led_win) at(l[0]) translate([0, 0, shroud_z - eps]) cylinder(d = l[1], h = shell_d - shroud_z + 2 * eps);
}
module face_tubes() {
    at(sw_reset) translate([0, 0, z_fin - guide_h]) cylinder(d = guide_od, h = guide_h + eps);
    for (p = [sw_s3en, sw_s3boot]) at(p) translate([0, 0, tube_z]) cylinder(d = tube_od, h = z_fin - tube_z + eps);
    for (l = led_win) at(l[0]) translate([0, 0, shroud_z]) cylinder(d = l[1] + 1.6, h = z_fin - shroud_z + eps);
}

module label_recess(c, wh, z) {
    if (label_t > 0) translate([c[0] - wh[0] / 2, Y(c[1]) - wh[1] / 2, z]) cube([wh[0], wh[1], label_t + eps]);
}

// ---------------------------------------------------------- board holding --
// front: ribs on F.Cu along the sides' lower part (the parts reach the edges higher up)
module side_ribs() {
    for (r = rib_boxes) {
        x0 = max(r[0], sx0 + wall - eps);  x1 = min(r[2], sx1 - wall + eps);
        translate([x0, Y(r[3]) - eps, z_f]) cube([x1 - x0, r[3] - r[1] + eps, z_fin - z_f + eps]);
    }
}
// back: a ledge round the board's edge under B.Cu (B.Cu has no parts), and a pad under each button
module ledge2d() { difference() { inner2d(); offset(delta = -rib_w) board2d(); } }
module button_pads() {
    for (p = [sw_reset, sw_bootsel, sw_s3en, sw_s3boot]) at(p) translate([-2.5, -1.5, wall - eps]) cube([5, 3, gap_b + eps]);
}
// back: keys through the board's side notches, up into the front side ribs
module notch_keys(grow = 0, z0 = wall - eps, z1 = z_f + key_up) {
    for (n = pcb_notches)
        translate([n[0] + key_clr - grow - (n[0] < xc ? 2 : 0), Y(n[3]) + key_clr - grow, z0])
            cube([n[2] - n[0] - 2 * key_clr + 2 * grow + 2, n[3] - n[1] - 2 * key_clr + 2 * grow, z1 - z0]);
}
// back: snap-hook tongues at the top; their barbs catch pockets in the front half's top wall
module hook_tongues() {
    y_out = Y(y_in_top) - 0.15;      // the tongue's outer face, 0.15 off the front wall's inner face
    for (hx = hook_x) {
        translate([hx - hook_w / 2, y_out - hook_t, z_b - eps]) cube([hook_w, hook_t, hook_l + eps]);
        hull() {                     // barb: 63-degree catch below (firm pull releases it), 27-degree lead-in above
            translate([hx - hook_w / 2, y_out - eps, z_b + hook_l - 1.5]) cube([hook_w, eps, 0.01]);
            translate([hx - hook_w / 2, y_out - eps, z_b + hook_l - 1.2]) cube([hook_w, barb + eps, 0.01]);
            translate([hx - hook_w / 2, y_out - eps, z_b + hook_l - 0.01]) cube([hook_w, eps, 0.01]);
        }
    }
}
module hook_pockets() {
    for (hx = hook_x)
        translate([hx - hook_w / 2 - 0.3, Y(y_in_top) - 0.5, z_b + hook_l - 1.6])
            cube([hook_w + 0.6, 0.5 - 0.15 + barb + 0.2, 1.8]);
}
module lip_seat() { translate([0, 0, z_b - eps]) linear_extrude(lip + 0.2) offset(delta = 0.15) lip2d(); }

// ------------------------------------------------------------------ parts --
module front_half() {
    difference() {
        union() {
            translate([0, 0, z_fin]) linear_extrude(wall) outer2d();                            // front plate
            translate([0, 0, z_b]) linear_extrude(shell_d - z_b) difference() { outer2d(); inner2d(); }
            side_ribs();
            posts() {
                translate([0, 0, z_f]) cylinder(d = post_d, h = z_fin - z_f + eps);               // collar on F.Cu
                translate([0, 0, z_b - spig_in]) cylinder(d = spig_d, h = z_f - z_b + spig_in + eps);   // spigot
            }
            face_tubes();
        }
        posts() translate([0, 0, z_b - spig_in - eps]) cylinder(d = pilot_d, h = pilot_top - (z_b - spig_in) + eps);
        notch_keys(grow = 0.2, z0 = z_b - eps, z1 = z_f + key_up + 0.3);                        // key sockets
        face_cuts();
        lip_seat();
        board_slot();
        top_openings();
        side_openings();
        sd_notch();
        if (hooks) hook_pockets();
        label_recess(label_front_c, label_front, shell_d - label_t);
    }
}

module back_half() {
    difference() {
        union() {
            linear_extrude(wall) outer2d();                                                    // back plate
            linear_extrude(z_b) difference() { outer2d(); inner2d(); }                        // walls to the parting plane
            translate([0, 0, wall - eps]) linear_extrude(gap_b + eps) ledge2d();               // B.Cu rests on the ledge,
            posts() cylinder(d = post_d, h = z_b);                                             // the bosses
            button_pads();                                                                     // and under the buttons
            translate([0, 0, z_b - eps]) linear_extrude(lip + eps) lip2d();                     // alignment lip
            intersection() { notch_keys(); linear_extrude(shell_d) inner2d(); }
            if (hooks) hook_tongues();
        }
        posts() {
            translate([0, 0, -eps]) cylinder(d = screw_d, h = z_b + 2 * eps);
            translate([0, 0, -eps]) cylinder(d = head_d, h = head_h + eps);
            translate([0, 0, z_b - spig_in - 0.2]) cylinder(d = spig_d + 0.4, h = spig_in + 0.2 + eps);   // spigot socket
        }
        board_slot();
        top_openings();
        side_openings();
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
    translate([0, 0, z_b + shrink]) linear_extrude(pcb_t - 2 * shrink) offset(delta = -shrink)
        difference() { board2d(); for (h = pcb_holes) at(h) circle(d = h[2]); }
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
else if (part == "section")      // cut through the posts, seen from the top
    difference() { assembled(); translate([sx0 - 1, Y(pcb_holes[0][1]), -1]) cube([shell_w + 2, shell_h, shell_d + 2]); }
else if (part == "check") {      // must be empty: the board and the plunger only touch the shell
    intersection() { board(0.05); front_half(); }
    intersection() { board(0.05); back_half(); }
    intersection() { plunger_fitted(0.05); front_half(); }
}
else if (part == "parts_check") {    // must be empty: every part's courtyard box, to its height, clears the shell
    intersection() { part_boxes(); front_half(); }
    intersection() { part_boxes(); back_half(); }
}
else if (part == "parts_control")    // must NOT be empty: the same boxes raised 2.5 mm meet the front plate
    intersection() { part_boxes(2.5); front_half(); }
else {
    back_half();
    translate([shell_w + 12, 0, 0]) front_print();
    translate([sx1 + 6, Y(y_bot) + 8, 0]) plunger();
}
