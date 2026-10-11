// FujiNet-StudioII Rev0 cartridge shell (parametric, two-piece clamshell)
// ---------------------------------------------------------------------------
// The board is FliP's Studio II multicart outline grown 28 mm taller for the ESP32-S3 half
// (90.9 x 111.5 mm), so an original shell no longer fits.  This shell holds it the way an original
// holds FliP's board: two posts through the 8.128 mm holes, and keys in the side notches where the
// original's rivets go.  The bottom 15 mm of the board stays bare, to enter the console.  No
// original shell or console was measured: case/case-spec.md has every number and its source, and
// the ones marked VERIFY there are estimates.
//
// Coordinate frame = the KiCad board frame, so the generated anchors drop in:
//   X = board x (mm),  Y = -(board y)  (+Y up, away from the console),
//   Z = 0 at the outside of the BACK half, Z grows toward the player.
// FRONT half = over the component side (F.Cu: every part), which faces the console's FRONT, toward
//              the player.  It has the buttons, the LED windows and a small label recess.
// BACK  half = over B.Cu (the contacts' face, no parts), which faces the console's back.  An
//              original cartridge's picture label faces that way (EJK: "CART LABEL PIC TO BACK OF
//              CONSOLE").  It has the label recess and the two screw heads.
// The halves meet at the board's B.Cu face.  Two M3 screws go in from the back half, through the
// back bosses, into the front half's spigots, which pass through the board's holes.  Two snap
// hooks hold the top: the board has no holes up there, where the ESP32-S3's antenna is.
//
// Print: both halves outside-down, no supports, 0.2 mm layers, PETG (or PLA).  No carbon-fibre or
// metal-filled filament: the antenna is behind the top wall.
// Screws: 2x M3x12 pan head, self-tapping into the 2.6 mm pilots.  For M3 heat-set inserts, open the
// pilots to 4.0 mm (pilot_d) and use M3x8.

include <board-anchors.scad>

// ------------------------------------------------------------ parameters --
wall      = 2.0;    // walls and plates
lip       = 1.0;    // back half's alignment lip (an inset rim up into the front half)
clr       = 0.5;    // board edge to the lip
r_out     = 3.0;    // outer corner radius (plan view)
gap_b     = 3.0;    // back plate to B.Cu (no parts on B.Cu); sets the board's depth in the shell (VERIFY)
gap_f     = 7.4;    // F.Cu to the front plate: the 3.3 mm parts, the RESET plunger, a fitted debug header
board_out = 15.0;   // bare board below the shell, entering the console (VERIFY: ~15 on an original)
post_d    = 11.0;   // post collars and bosses (the H1 / H2 courtyards keep an 11.3 mm part-free ring)
spig_d    = 7.8;    // front spigot through the board's 8.128 mm hole
spig_in   = 1.0;    // ... reaching this far into the back boss's socket (registers the halves)
screw_d   = 3.4;    // M3 clearance through the back boss
pilot_d   = 2.6;    // spigot pilot: 2.6 self-tap, 4.0 for heat-set inserts
head_d    = 6.2;    // pan-head counterbore in the back plate
head_h    = 1.6;
rib_w     = 1.2;    // front side ribs and the back ledge reach this far onto the board (no courtyard
                    // closer than 2.27 mm to a side edge: C32 west, J3 east)
key_clr   = 0.15;   // notch keys: radial clearance in the board's notches
key_up    = 1.0;    // ... rising this far above F.Cu into sockets in the front side ribs
hooks     = true;   // the two snap hooks at the top
hook_x    = [80, 120];  // their centres: inside the antenna band (plastic only), clear of the openings
hook_w    = 8.0;
hook_t    = 1.0;    // tongue thickness
hook_l    = 6.5;    // tongue height above the parting plane
barb      = 0.6;    // barb depth: the tongue flexes 0.45 mm going in (1.6 % strain)
label_t   = 0.4;    // label recess depth (0: none)
label_back   = [60, 80];    // back face: the picture label, between the screw heads
label_back_c = [100, 79];   // its centre (board x, y)
dbg_window = true;  // a window over J2 (the DNP debug UART): a fitted header takes a 1x3 plug with the shell on
sw_h      = 1.5;    // TS-1187A above F.Cu (XKB drawing; tools/make_fp_extra.py)
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
top_r   = pcb_outline[0][0] - pcb_x0;          // the board's rounded top corners (3 mm)
dbg_c   = [dbg_header[0] - 2.54, dbg_header[1]];   // J2's middle pin: the 1x03 runs west from pin 1
                                                   // (the footprint at rotation -90)
sd_x    = microsd[0] + 0.9;          // the card's centreline: the TF-015's pegs (x 131.3 / 139.3) straddle
                                     // the card, 0.9 mm east of the footprint origin (rotation 180)
guide_od = 11.0;  guide_id = 8.8;  guide_h = 3.4;  // RESET plunger guide below the front plate
cap_d   = 5.8;  cap_hole = 6.2;  fl_d = 8.4;  stem_d = 3.0;
tube_od = pin_d + 2.2;               // pin-hole guide tubes
tube_z  = z_f + sw_h + 1.0;          // ... ending 1 mm above the buttons
shroud_z = z_f + 2.0;                // LED shrouds end 2 mm above F.Cu, over the buttons (1.5); the S3 module
                                     // (3.1) is beside the WS2812's, 0.13 mm outside its courtyard
pilot_top = shell_d - 1.4;           // the pilot stops 1.4 mm short of the front face

function Y(y) = -y;                  // board y -> shell Y
function d2(a, b) = norm([a[0] - b[0], a[1] - b[1]]);
function inside(p, c, wh, m) = abs(p[0] - c[0]) < wh[0] / 2 + m && abs(p[1] - c[1]) < wh[1] / 2 + m;

face_holes = concat([[sw_reset, cap_hole], [sw_bootsel, tube_od], [sw_s3en, tube_od], [sw_s3boot, tube_od]],
                    [for (l = led_win) [l[0], l[1] + 1.6]]);    // [centre, outer diameter]

// the numbers the board and the console need, checked
assert(sx0 + wall + lip + clr <= pcb_x0 + 1e-6 && pcb_x1 <= sx1 - wall - lip - clr + 1e-6, "board wider than the cavity");
assert(gap_f >= parts_max_h + 0.8, "parts too tall for the front gap");
assert(!dbg_window || gap_f + wall >= dbg_header_h, "a fitted debug header would stand proud of the front face");
assert(y_in_bot >= parts_min_y, "the bottom wall would sit on parts");
assert(len([for (n = pcb_notches) if (n[1] + n[2] + 1.0 > y_in_bot) 1]) == 0, "a notch key outside the shell");
assert(board_out >= 9.55, "the shell would cover the contacts (copper to 8.95 mm, mask to 9.05)");
assert(len([for (h = pcb_holes) if (d2(h, esp32_ant) < 15 + head_d / 2) 1]) == 0, "a screw within 15 mm of the antenna");
assert(len([for (p = [sw_bootsel, sw_s3boot, sw_s3en]) if (d2(p, sw_reset) < guide_od / 2 + tube_od / 2 + 0.4) 1]) == 0,
       "the RESET guide meets a pin-hole tube");
assert(len([for (f = face_holes) if (inside(f[0], label_xy, label_wh, f[1] / 2 + 1)) 1]) == 0, "a face hole in the front label");
assert(!dbg_window || !inside(dbg_c, label_xy, label_wh, 3), "the debug window in the front label");
assert(len([for (h = pcb_holes) if (inside(h, label_back_c, label_back, head_d / 2 + 1)) 1]) == 0, "a screw head in the back label");
assert(len([for (hx = hook_x) if (abs(hx - usb_c[0]) < hook_w / 2 + 7.5 || abs(hx - sd_x) < hook_w / 2 + 8) 1]) == 0,
       "a hook in the USB-C or microSD opening");
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
// USB-C and microSD leave through the top wall (both halves); the ESP32-S3's antenna, between
// them, has only plastic over it.
module top_openings() {
    // USB-C: receptacle 8.94 x 3.26, its centre 1.63 above F.Cu; the opening takes a plug's
    // overmold (up to 12.5 x 7), which stops at the receptacle's face 0.46 mm past the board edge
    translate([usb_c[0] - 6.5, Y(pcb_y0) - eps, z_f + 1.63 - 3.6]) cube([13, pcb_y0 - y_top + 2 * eps, 7.2]);
    // microSD: the card (11 x 0.8) enters ~1 mm above F.Cu; latched, it stands 2.5 mm proud of the
    // TF-015's face (0.5 mm inside the board edge), so 1.5 mm inside the shell's top face
    translate([sd_x - 7, Y(pcb_y0) - eps, z_f + 0.2]) cube([14, pcb_y0 - y_top + 2 * eps, 2.4]);
}
// the front half's top wall open over the card, from the slot to the front face: the latched card's
// end is then in reach of a thumb, to push the push-push card home (and nothing bridges the slot)
module sd_notch() { translate([sd_x - 7, Y(pcb_y0) - eps, z_f + 0.2]) cube([14, pcb_y0 - y_top + 2 * eps, shell_d - z_f]); }

// front face: RESET through a plunger; BOOTSEL, S3 EN, S3 BOOT through pin-holes; LED windows;
// the debug window
module face_cuts() {
    at(sw_reset) {
        translate([0, 0, z_fin - eps]) cylinder(d = cap_hole, h = wall + 2 * eps);
        translate([0, 0, z_fin - guide_h - eps]) cylinder(d = guide_id, h = guide_h + eps);
    }
    for (p = [sw_bootsel, sw_s3en, sw_s3boot]) at(p) translate([0, 0, tube_z - eps]) cylinder(d = pin_d, h = shell_d - tube_z + 2 * eps);
    for (l = led_win) at(l[0]) translate([0, 0, shroud_z - eps]) cylinder(d = l[1], h = shell_d - shroud_z + 2 * eps);
    if (dbg_window) at(dbg_c) translate([-4.7, -1.8, z_fin - eps]) cube([9.4, 3.6, wall + 2 * eps]);
}
module face_tubes() {
    at(sw_reset) translate([0, 0, z_fin - guide_h]) cylinder(d = guide_od, h = guide_h + eps);
    for (p = [sw_bootsel, sw_s3en, sw_s3boot]) at(p) translate([0, 0, tube_z]) cylinder(d = tube_od, h = z_fin - tube_z + eps);
    for (l = led_win) at(l[0]) translate([0, 0, shroud_z]) cylinder(d = l[1] + 1.6, h = z_fin - shroud_z + eps);
}

module label_recess(c, wh, z) {
    if (label_t > 0) translate([c[0] - wh[0] / 2, Y(c[1]) - wh[1] / 2, z]) cube([wh[0], wh[1], label_t + eps]);
}

// ---------------------------------------------------------- board holding --
// front: ribs on F.Cu along the straight sides (below the rounded top corners)
module side_ribs() {
    for (s = [[sx0 + wall - eps, pcb_x0 + rib_w], [pcb_x1 - rib_w, sx1 - wall + eps]])
        translate([s[0], Y(y_in_bot) - eps, z_f]) cube([s[1] - s[0], y_in_bot - pcb_y0 - top_r + eps, z_fin - z_f + eps]);
}
// back: a ledge round the board's edge under B.Cu (B.Cu has no parts), and a rib under the buttons
module ledge2d() { difference() { inner2d(); offset(delta = -rib_w) board2d(); } }
module button_rib() {
    xs = [sw_s3en[0], sw_bootsel[0], sw_reset[0], sw_s3boot[0]];
    translate([min(xs) - 4, Y(sw_reset[1]) - 1.5, wall - eps]) cube([max(xs) - min(xs) + 8, 3, gap_b + eps]);
}
// back: keys through the board's side notches (the original's rivets), up into the front side ribs
module notch_keys(grow = 0, z0 = wall - eps, z1 = z_f + key_up) {
    for (n = pcb_notches) translate([n[0], Y(n[1]), z0]) cylinder(r = n[2] - key_clr + grow, h = z1 - z0);
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
        sd_notch();
        if (hooks) hook_pockets();
        label_recess(label_xy, label_wh, shell_d - label_t);
    }
}

module back_half() {
    difference() {
        union() {
            linear_extrude(wall) outer2d();                                                    // back plate
            linear_extrude(z_b) difference() { outer2d(); inner2d(); }                        // walls to the parting plane
            translate([0, 0, wall - eps]) linear_extrude(gap_b + eps) ledge2d();               // B.Cu rests on the ledge,
            posts() cylinder(d = post_d, h = z_b);                                             // the bosses
            button_rib();                                                                      // and under the buttons
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
        label_recess(label_back_c, label_back, -eps);
    }
}

// RESET plunger, modelled cap-down (its print orientation): the cap through the 6.2 mm hole, a 45-degree
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

// the board, for the "assembled" / "section" / "check" views
module board(shrink = 0) {
    translate([0, 0, z_b + shrink]) linear_extrude(pcb_t - 2 * shrink) offset(delta = -shrink)
        difference() { board2d(); for (h = pcb_holes) at(h) circle(d = h[2]); }
}
module assembled() {
    color("khaki") back_half();
    color("khaki", 0.6) front_half();
    color("green") board();
    color("red") plunger_fitted();
}

// print orientation: turned over (a rotation, never a mirror: mirroring gives the half's mirror image)
module front_print() {             // turned about its own middle, so it lands on the back half's footprint
    translate([0, Y(y_top) + Y(y_bot), shell_d]) rotate([180, 0, 0]) front_half();
}

// ---------------------------------------------------------------- output --
part = "both";   // "front", "back", "plunger", "both" (print layout), "assembled", "section", "check"
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
else {
    back_half();                                       // 2 x 97.9 + 12 = 208 x 100 mm
    translate([shell_w + 12, 0, 0]) front_print();
    translate([sx1 + 6, Y(y_bot) + 8, 0]) plunger();
}
