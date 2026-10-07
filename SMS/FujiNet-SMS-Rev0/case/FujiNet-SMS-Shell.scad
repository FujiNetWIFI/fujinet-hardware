// FujiNet-SMS Rev0 cartridge shell (parametric, two-piece clamshell)
// ---------------------------------------------------------------------------
// A Sega Master System cartridge's base -- 109.1 x 16.9 mm, the board's
// component face 8.3 mm inside the label face, the contact edge ~5.4 mm up
// inside an open connector mouth -- grown taller (the original is 69.3 mm)
// to hold the 100 mm-wide FujiNet board.  case/case-spec.md has every number
// and its source; the ones marked VERIFY there were not measured on a real
// cartridge or console.
//
// Coordinate frame = the KiCad board frame, so the generated anchors drop in:
//   X = board x (mm),  Y = -(board y)  (+Y up, away from the console),
//   Z = 0 at the outside of the REAR half, Z grows toward the label face.
// FRONT half = the label face, over the component side (F.Cu: every part,
//              the even fingers).  Buttons, LED windows and the label are here.
// REAR  half = the back plate, over the B.Cu side (no parts).
// The two halves meet at the board's B.Cu face; four M3 screws go in from the
// back through the board's holes into the front half's bosses.
//
// Print: both halves outside-down, no supports, 0.2 mm layers, PETG or PLA.
// Screws: 4x M3x12 pan head (self-tapping into the 2.6 mm pilots, or open the
// pilots to 4.0 mm for M3 heat-set inserts and use M3x10).

include <board-anchors.scad>

// ------------------------------------------------------------ parameters --
shell_w  = 109.1;   // original SMS shell width (bsittler, caliper) -- the slot's limit
shell_d  = 16.9;    // original depth
seat_f   = 8.3;     // label (outer) face -> board F.Cu face, as the original seats its board (VERIFY)
edge_in  = 5.4;     // the contact edge sits this far up inside the shell's bottom (VERIFY)
wall     = 2.0;     // walls and plates
clr      = 0.5;     // board-to-wall clearance at the top edge
r_out    = 3.0;     // outer corner radius
mouth_w  = 76.0;    // connector mouth in the bottom wall (the 65.8 tab + the console's housing; VERIFY)
lip      = 1.0;     // rear half's alignment lip (inset rim up into the front half)
boss_f_d = 5.6;     // front bosses (board keeps a 3 mm part-free ring round each hole)
boss_r_d = 6.0;     // rear bosses (no parts on B.Cu)
screw_d  = 3.4;     // clearance through the rear half and the board
pilot_d  = 2.6;     // front pilot (self-tap); 4.0 for heat-set inserts
head_d   = 6.2;     // pan-head counterbore in the back plate
head_h   = 1.6;
label    = [74, 36];                // label recess (w, h), lower front face, clear of the buttons and LEDs
label_c  = [103, 90];               // its centre (board x, y)
label_t  = 0.4;
part_h   = 3.3;     // tallest part above F.Cu (USB-C 3.2, ESP32-S3 module 3.1)

$fn = 48;
eps = 0.01;

// ---------------------------------------------------------- derived frame --
z_b   = shell_d - seat_f - pcb_t;   // board B.Cu face (the parting plane)
z_f   = shell_d - seat_f;           // board F.Cu face
z_fin = shell_d - wall;             // front plate's inner face
xc    = (pcb_x0 + pcb_x1) / 2;
sx0   = xc - shell_w / 2;  sx1 = xc + shell_w / 2;
y_bot = pcb_y1 + edge_in;           // shell bottom (board y)
y_top = pcb_y0 - clr - wall;        // shell top (board y)
shell_h = y_bot - y_top;

function Y(y) = -y;                 // board y -> shell Y

// the numbers the slot and the board need, checked
assert(abs(shell_w - 109.1) < 0.01, "the base must stay the original SMS width");
assert(sx0 + wall + 0.5 <= pcb_x0 && pcb_x1 <= sx1 - wall - 0.5, "board wider than the cavity");
assert(z_fin - z_f >= part_h + 0.8, "parts too tall for the front gap");
assert(z_b >= wall + 1.0, "no room behind the board");
assert(mouth_w >= pcb_tab_x1 - pcb_tab_x0 + 4, "mouth narrower than the tab");
echo(str("shell: ", shell_w, " x ", shell_h, " x ", shell_d, " mm (original 109.1 x 69.3 x 16.9); ",
         "front gap ", z_fin - z_f, " mm, rear gap ", z_b - wall, " mm"));

// ---------------------------------------------------------------- outline --
module outer2d() {
    translate([sx0 + r_out, Y(y_bot) + r_out]) offset(r = r_out)
        square([shell_w - 2 * r_out, shell_h - 2 * r_out]);
}
module inner2d() { offset(delta = -wall) outer2d(); }
module lip2d()   { difference() { offset(delta = -wall) outer2d(); offset(delta = -wall - lip) outer2d(); } }

module screws() { for (h = pcb_holes) translate([h[0], Y(h[1])]) children(); }

// ------------------------------------------------------------ openings ---
// USB-C and microSD leave through the top wall; the S3 antenna (top-left)
// has only plastic over it.
module top_openings() {
    // USB-C: receptacle 8.9 x 3.2, centre ~1.6 mm above F.Cu; opening for a plug overmold
    translate([usb_c[0] - 6.5, Y(pcb_y0) - eps, z_f + 1.6 - 3.6]) cube([13, clr + wall + 2 * eps, 7.2]);
    // microSD: card 11 x 0.8, ~1.0 mm above F.Cu; slot, and a finger notch in the label face
    // to push the push-push card home (its end sits ~0.5 mm inside the shell)
    translate([microsd[0] - 7, Y(pcb_y0) - eps, z_f + 0.2]) cube([14, clr + wall + 2 * eps, 2.4]);
    translate([microsd[0], Y(y_top) - 1.5, shell_d]) scale([1, 0.6, 1]) sphere(d = 12);
}
// the connector mouth: the bottom wall is open across the tab, through the full depth
module mouth() {
    translate([xc - mouth_w / 2, Y(y_bot) - eps, wall]) cube([mouth_w, wall + 2 * eps, shell_d - 2 * wall]);
}
// label face: RESET (with a plunger), the other three buttons as pin-holes, LED windows
module face_holes() {
    for (p = [[sw_reset, 6.2], [sw_bootsel, 2.2], [sw_s3_en, 2.2], [sw_s3_boot, 2.2],
              [led_ws, 3.0], [led_rp, 2.0]])
        translate([p[0][0], Y(p[0][1]), z_fin - eps]) cylinder(d = p[1], h = wall + 2 * eps);
}

// ------------------------------------------------------------------ parts --
module front_half() {
    difference() {
        union() {
            translate([0, 0, z_fin]) linear_extrude(wall) outer2d();                        // label plate
            translate([0, 0, z_b]) linear_extrude(shell_d - z_b) difference() { outer2d(); inner2d(); }
            screws() translate([0, 0, z_f]) cylinder(d = boss_f_d, h = z_fin - z_f + eps);   // board stops
            // RESET plunger guide
            translate([sw_reset[0], Y(sw_reset[1]), z_f + 2.6]) cylinder(d = 9, h = z_fin - z_f - 2.6 + eps);
        }
        screws() translate([0, 0, z_f - eps]) cylinder(d = pilot_d, h = z_fin - z_f - 0.4);
        translate([sw_reset[0], Y(sw_reset[1]), z_f + 2.6 - eps]) cylinder(d = 6.4, h = z_fin - z_f);
        face_holes();
        top_openings();
        mouth();
        lip_seat();
        translate([label_c[0] - label[0] / 2, Y(label_c[1]) - label[1] / 2, shell_d - label_t])
            cube([label[0], label[1], label_t + eps]);
    }
}
module lip_seat() { translate([0, 0, z_b - eps]) linear_extrude(lip + 0.2) offset(delta = 0.15) lip2d(); }

module rear_half() {
    difference() {
        union() {
            linear_extrude(wall) outer2d();                                                  // back plate
            linear_extrude(z_b) difference() { outer2d(); inner2d(); }                      // walls to the parting plane
            translate([0, 0, z_b - eps]) linear_extrude(lip) lip2d();                         // alignment lip
            screws() cylinder(d = boss_r_d, h = z_b);                                         // board rests on these
        }
        screws() translate([0, 0, -eps]) cylinder(d = screw_d, h = z_b + 2 * eps);
        screws() translate([0, 0, -eps]) cylinder(d = head_d, h = head_h + eps);
        mouth();
        top_openings();
    }
}

// RESET plunger: a cap through the label plate, a flange under it, a stem onto the TL3342
module plunger() {
    cylinder(d = 6.0, h = 1.2 + wall);                    // cap: through the 6.2 hole, 1.2 proud
    translate([0, 0, -1.0]) cylinder(d = 8.4, h = 1.0);   // flange inside the 9 mm guide
    translate([0, 0, -(z_fin - z_f - 2.6 - 1.0)]) cylinder(d = 3.0, h = z_fin - z_f - 2.6 - 1.0 + eps);
}

// ---------------------------------------------------------------- output --
part = "both";   // "front", "rear", "plunger", "both" (print layout), "assembled"
if (part == "front") translate([0, 0, shell_d]) mirror([0, 0, 1]) front_half();
else if (part == "rear") rear_half();
else if (part == "plunger") plunger();
else if (part == "assembled") { front_half(); rear_half();
                                translate([sw_reset[0], Y(sw_reset[1]), z_fin - 0.4]) plunger(); }
else {
    translate([0, 0, shell_d]) mirror([0, 0, 1]) front_half();
    translate([shell_w + 10, 0, 0]) rear_half();
}
