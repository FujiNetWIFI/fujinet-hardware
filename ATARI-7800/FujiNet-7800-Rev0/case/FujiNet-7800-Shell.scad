// FujiNet-7800 Rev0 cartridge shell (parametric, two-piece clamshell)
// ---------------------------------------------------------------------------
// A 7800 cartridge's base -- the width and depth the console's slot takes, the board centred in
// the depth, the contact edge recessed inside an open connector mouth -- grown taller to hold the
// 72.4 x 115 mm FujiNet board.  case/case-spec.md has every number and its source; the ones
// marked VERIFY there were not measured on a real 7800 cartridge or console.
//
// Coordinate frame = the KiCad board frame, so the generated anchors drop in:
//   X = board x (mm),  Y = -(board y)  (+Y up, away from the console),
//   Z = 0 at the outside of the BACK half, Z grows toward the label face.
// LABEL half = over the component side (F.Cu: every part, pins 1-16), which faces the console's
//              REAR -- the face a 7800 cartridge's label faces ("hold the cartridge so the name on
//              the label faces away from you").  Buttons, LED windows and the label recess are here.
// BACK  half = over B.Cu (no parts), toward the player.
// The two halves meet at the board's B.Cu face; four M3 screws go in from the back half through
// the board's holes into the label half's bosses.
//
// Print: both halves outside-down, no supports, 0.2 mm layers, PETG or PLA.
// Screws: 4x M3x12 pan head (self-tapping into the 2.6 mm pilots, or open the pilots to 4.0 mm
// for M3 heat-set inserts and use M3x10).

include <board-anchors.scad>

// ------------------------------------------------------------ parameters --
shell_w  = 80.0;    // outside width: the 72.4 board + 2 x (2 wall + 1 lip + 0.8 clearance); <= the
                    // 81.5 mm 2600 cartridge the 7800's slot also takes (VERIFY on a 7800 cartridge)
shell_d  = 20.0;    // outside depth, as a 2600 / 7800 cartridge (2600: 20.2, norm8332) (VERIFY)
edge_in  = 6.5;     // the contact edge sits this far up inside the shell's bottom (VERIFY)
wall     = 2.0;     // walls and plates
clr      = 0.5;     // board-to-lip clearance (the board's top edge sits lip + clr inside the top wall)
r_out    = 3.0;     // outer corner radius
mouth_w  = 57.0;    // connector mouth in the bottom wall: the 47 mm tab + the console's connector
                    // housing either side (VERIFY)
lip      = 1.0;     // back half's alignment lip (inset rim up into the label half)
boss_l_d = 5.6;     // label-half bosses (the board keeps a 3 mm part-free ring round each hole)
boss_b_d = 6.0;     // back-half bosses (no parts on B.Cu)
screw_d  = 3.4;     // clearance through the back half and the board
pilot_d  = 2.6;     // label-half pilot (self-tap); 4.0 for heat-set inserts
head_d   = 6.2;     // pan-head counterbore in the back plate
head_h   = 1.6;
label    = [54, 38];                // label recess (w, h) on the label face, clear of buttons and LEDs
label_c  = [104, 104];              // its centre (board x, y)
label_t  = 0.4;
part_h   = 3.3;     // tallest part above F.Cu (USB-C 3.2, ESP32-S3 module 3.1)
// RESET plunger and its guide.  The four buttons stand in one column at 6.2 mm, so the guide must stay
// under ~9.4 mm across to clear the pin-holes either side: a small cap and flange.
sw_h      = 1.5;    // TS-1187A above F.Cu (XKB drawing; tools/make_fp_extra.py)
proud     = 0.6;    // the cap above the label face at rest
press_gap = 0.15;   // the stem above the switch at rest
cap_d = 5.0;  cap_hole = 5.4;  fl_d = 6.6;  stem_d = 3.0;   // cap, its hole, flange, stem
guide_od = 8.6;  guide_id = 7.0;  guide_h = 3.4;          // guide below the label plate

$fn = 48;
eps = 0.01;

// ---------------------------------------------------------- derived frame --
z_b   = (shell_d - pcb_t) / 2;      // board B.Cu face (the parting plane): board centred in the depth
z_f   = z_b + pcb_t;                // board F.Cu face
z_fin = shell_d - wall;             // label plate's inner face
xc    = (pcb_x0 + pcb_x1) / 2;
sx0   = xc - shell_w / 2;  sx1 = xc + shell_w / 2;
y_bot = pcb_y1 + edge_in;           // shell bottom (board y)
y_top = pcb_y0 - clr - lip - wall;  // shell top (board y): the lip runs round the inside
shell_h = y_bot - y_top;

function Y(y) = -y;                 // board y -> shell Y

// the numbers the slot and the board need, checked
assert(shell_w <= 81.5, "wider than a 2600 cartridge: the slot may not take it");
assert(sx0 + wall + lip + clr <= pcb_x0 && pcb_x1 <= sx1 - wall - lip - clr, "board wider than the cavity");
assert(z_fin - z_f >= part_h + 0.8, "parts too tall for the label-side gap");
assert(z_b >= wall + 1.0, "no room behind the board");
assert(mouth_w >= pcb_tab_x1 - pcb_tab_x0 + 4, "mouth narrower than the tab");
assert(mouth_w <= shell_w - 2 * wall - 2, "mouth wider than the cavity");
assert(len([for (p = [sw_bootsel, sw_s3_en, sw_s3_boot])
            if (norm([p[0] - sw_reset[0], p[1] - sw_reset[1]]) < guide_od / 2 + 2.2 / 2 + 0.4) 1]) == 0,
       "the RESET guide meets a pin-hole");
assert(z_fin - guide_h >= z_f + part_h + 0.3, "the RESET guide would sit on parts");
echo(str("shell: ", shell_w, " x ", shell_h, " x ", shell_d, " mm; label-side gap ", z_fin - z_f,
         " mm, back gap ", z_b - wall, " mm; edge ", edge_in, " mm inside the mouth"));

// ---------------------------------------------------------------- outline --
module outer2d() {
    translate([sx0 + r_out, Y(y_bot) + r_out]) offset(r = r_out)
        square([shell_w - 2 * r_out, shell_h - 2 * r_out]);
}
module inner2d() { offset(delta = -wall) outer2d(); }
module lip2d()   { difference() { offset(delta = -wall) outer2d(); offset(delta = -wall - lip) outer2d(); } }

module screws() { for (h = pcb_holes) translate([h[0], Y(h[1])]) children(); }

// ------------------------------------------------------------ openings ---
// USB-C and microSD leave through the top wall; the S3 antenna (top-left) has only plastic over it.
module top_openings() {
    // USB-C: receptacle 8.9 x 3.2, centre ~1.6 mm above F.Cu; opening for a plug overmold
    translate([usb_c[0] - 6.5, Y(pcb_y0) - eps, z_f + 1.6 - 3.6]) cube([13, clr + lip + wall + 2 * eps, 7.2]);
    // microSD: card 11 x 0.8, ~1.0 mm above F.Cu; slot, and a finger notch in the label face
    // to push the push-push card home
    translate([microsd[0] - 7, Y(pcb_y0) - eps, z_f + 0.2]) cube([14, clr + lip + wall + 2 * eps, 2.4]);
    translate([microsd[0], Y(y_top) - 1.5, shell_d]) scale([1, 0.6, 1]) sphere(d = 12);
}
// the connector mouth: the bottom wall open across the tab, through the full inner depth (the
// console's plastic keys enter the board's two key slots inside it)
module mouth() {
    translate([xc - mouth_w / 2, Y(y_bot) - eps, wall]) cube([mouth_w, wall + 2 * eps, shell_d - 2 * wall]);
}
// label face: RESET (with a plunger), the other three buttons as pin-holes, LED windows
module face_holes() {
    for (p = [[sw_reset, cap_hole], [sw_bootsel, 2.2], [sw_s3_en, 2.2], [sw_s3_boot, 2.2],
              [led_ws, 3.0], [led_rp, 2.0]])
        translate([p[0][0], Y(p[0][1]), z_fin - eps]) cylinder(d = p[1], h = wall + 2 * eps);
}

// ------------------------------------------------------------------ parts --
module label_half() {
    difference() {
        union() {
            translate([0, 0, z_fin]) linear_extrude(wall) outer2d();                        // label plate
            translate([0, 0, z_b]) linear_extrude(shell_d - z_b) difference() { outer2d(); inner2d(); }
            screws() translate([0, 0, z_f]) cylinder(d = boss_l_d, h = z_fin - z_f + eps);   // board stops
            // RESET plunger guide
            translate([sw_reset[0], Y(sw_reset[1]), z_fin - guide_h]) cylinder(d = guide_od, h = guide_h + eps);
        }
        screws() translate([0, 0, z_f - eps]) cylinder(d = pilot_d, h = z_fin - z_f - 0.4);
        translate([sw_reset[0], Y(sw_reset[1]), z_fin - guide_h - eps]) cylinder(d = guide_id, h = guide_h + eps);
        face_holes();
        top_openings();
        mouth();
        lip_seat();
        translate([label_c[0] - label[0] / 2, Y(label_c[1]) - label[1] / 2, shell_d - label_t])
            cube([label[0], label[1], label_t + eps]);
    }
}
module lip_seat() { translate([0, 0, z_b - eps]) linear_extrude(lip + 0.2) offset(delta = 0.15) lip2d(); }

module back_half() {
    difference() {
        union() {
            linear_extrude(wall) outer2d();                                                  // back plate
            linear_extrude(z_b) difference() { outer2d(); inner2d(); }                      // walls to the parting plane
            translate([0, 0, z_b - eps]) linear_extrude(lip) lip2d();                         // alignment lip
            screws() cylinder(d = boss_b_d, h = z_b);                                         // board rests on these
        }
        screws() translate([0, 0, -eps]) cylinder(d = screw_d, h = z_b + 2 * eps);
        screws() translate([0, 0, -eps]) cylinder(d = head_d, h = head_h + eps);
        mouth();
        top_openings();
    }
}

// RESET plunger, modelled cap-down (its print orientation): the cap through the label plate, a
// 45-degree cone (no support) into a flange held in the guide, a stem onto the TS-1187A.  At rest the
// cone sits on the hole's edge, the cap `proud` above the face and the stem `press_gap` above the switch.
cap_l    = wall + proud - (cap_hole - cap_d) / 2;
cone_h   = (fl_d - cap_d) / 2;
stem_end = wall + proud + (z_fin - z_f) - sw_h - press_gap;   // from the cap's top
module plunger() {
    cylinder(d = cap_d, h = cap_l + eps);
    translate([0, 0, cap_l]) cylinder(d1 = cap_d, d2 = fl_d, h = cone_h);
    translate([0, 0, cap_l + cone_h - eps]) cylinder(d = fl_d, h = 0.7 + eps);
    translate([0, 0, cap_l + cone_h + 0.7 - eps]) cylinder(d = stem_d, h = stem_end - (cap_l + cone_h + 0.7) + eps);
}
module plunger_fitted(drop = 0) {
    translate([sw_reset[0], Y(sw_reset[1]), shell_d + proud - drop]) rotate([180, 0, 0]) plunger();
}

// the board, for the "assembled" / "check" views
module board(shrink = 0) {
    translate([0, 0, z_b + shrink]) linear_extrude(pcb_t - 2 * shrink) polygon([for (p = pcb_outline) [p[0], Y(p[1])]]);
}

// ---------------------------------------------------------------- output --
part = "both";   // "label", "back", "plunger", "both" (print layout), "assembled", "check"
// print orientation: turned over by a rotation (a mirror would export the half's mirror image)
module label_print() { translate([0, Y(y_top) + Y(y_bot), shell_d]) rotate([180, 0, 0]) label_half(); }
if (part == "label") label_print();
else if (part == "back") back_half();
else if (part == "plunger") plunger();
else if (part == "assembled") { label_half(); back_half(); color("green") board(); color("red") plunger_fitted(); }
else if (part == "check") { intersection() { board(0.05); label_half(); }   // must be empty: the board
                            intersection() { board(0.05); back_half(); }    // only touches the bosses,
                            intersection() { plunger_fitted(0.05); label_half(); } }   // the plunger the hole's edge
else {
    label_print();
    translate([shell_w + 10, 0, 0]) back_half();
}
