// FujiNet-TRS80M1 Rev0 case (parametric, a tray and a lid)
// ---------------------------------------------------------------------------
// The board is a 100 x 76 mm rectangle with an M3 hole in each corner (tools/header_geom.py).  The case
// sits beside the Model I's keyboard unit, where the Expansion Interface would, on a short 40-wire
// ribbon: the ribbon's IDC socket enters the box header's mouth through the west wall.  The USB-C (the
// card's only power) comes in through the north wall, the microSD through the south wall.  No Model I,
// cable or printed case was measured: case/case-spec.md has every number and its source, and the ones
// marked VERIFY are estimates.  (FujiNet-ColecoVision Rev0's shell machinery: anchors, plunger, checks.)
//
// Coordinate frame = the KiCad board frame, so the generated anchors drop in:
//   X = board x (mm),  Y = -(board y)  (+Y = north),
//   Z = 0 at the outside of the TRAY's floor, Z grows up toward the lid (F.Cu, every part, faces up).
// TRAY = the floor, the walls up to the board's F.Cu face, four bosses the board rests on.
// LID  = the top plate and the walls from F.Cu up; RESET through a plunger, BOOTSEL / S3 BOOT / S3 EN
//        through recessed pin-holes, a window over the DIP switches, LED windows, a label recess.
// The halves meet at the board's F.Cu face; four M3 screws go in from under the tray, through its bosses
// and the board's holes, into the lid's bosses: the board is clamped between the two.
//
// Print: both halves outside-down, no supports, 0.2 mm layers, PETG (or PLA).  No carbon-fibre or
// metal-filled filament: the ESP32-S3's antenna is behind the east wall.
// Screws: 4x M3x16 pan head, self-tapping into the lid's 2.5 mm pilots (or M3 heat-set inserts:
// insert_d = 4.0, then M3x16 machine screws).

include <board-anchors.scad>

// ------------------------------------------------------------ parameters --
wall      = 2.0;    // walls and the lid's top plate
floor_t   = 2.0;    // tray floor
under     = 3.5;    // floor to B.Cu: the THT header's leads stand ~1.5 mm proud of B.Cu (VERIFY on a built board)
top_clr   = 9.6;    // F.Cu to the lid's inner face: the box header's shroud is 8.85-9.0 mm tall
side_clr  = 0.6;    // board edge to the inner wall faces (the header's mouth stands 0.24 mm past the board)
r_out     = 3.0;    // outer corner radius (plan view)
lip       = 1.0;    // the tray's alignment lip: the inner half of its wall rises this far into a rebate in the lid's
                    // wall (inside the wall's own thickness: nothing reaches over the board)
boss_d    = 7.0;    // bosses at the board's holes (hole_keep 3.6 mm: no part within 3.6 of a hole)
screw_d   = 3.4;    // M3 clearance through the tray boss and the board
pilot_d   = 2.5;    // lid boss pilot for an M3 self-tapping screw
insert_d  = 0;      // 4.0 for an M3 heat-set insert (0: the self-tapping pilot)
head_d    = 6.0;    // pan-head counterbore in the tray floor
head_h    = 2.0;
label_t   = 0.4;    // label recess depth (0: none)
label_c   = [76, 72];          // the lid's label, over the bus buffers (board x, y): clear of every opening
label_wh  = [40, 30];
sw_h      = 1.5;    // TS-1187A above F.Cu (XKB drawing)
proud     = 0.6;    // RESET plunger's cap above the lid
press_gap = 0.15;   // RESET plunger's stem above the button at rest
pin_d     = 2.2;    // pin-holes for BOOTSEL, S3 BOOT and S3 EN (a straightened paper clip)
dip_win   = [9.0, 7.6];        // window over the DIP switch body (7.6 x 6.1): a pen tip flips each slide
led_win   = [[led_status, 3.0, true], [led_rp, 2.0, true]];   // [centre, window, shroud]
hdr_open  = [61.0, 9.8];       // west-wall opening for the IDC socket: the shroud's 58.6 x 8.9 + clearance
                               // (a 2x20 IDC socket fits inside the shroud: the opening clears the shroud)

$fn = 48;
eps = 0.01;

// ---------------------------------------------------------- derived frame --
z_b     = floor_t + under;           // board B.Cu face
z_f     = z_b + pcb_t;               // board F.Cu face: the parting plane
z_lin   = z_f + top_clr;             // the lid's inner face
case_h  = z_lin + wall;              // overall height
cx0 = pcb_x0 - side_clr - wall;  cx1 = pcb_x1 + side_clr + wall;    // outside, board frame x
cy0 = pcb_y0 - side_clr - wall;  cy1 = pcb_y1 + side_clr + wall;    // outside, board frame y (north .. south)
case_w  = cx1 - cx0;  case_d = cy1 - cy0;
// RESET plunger (FujiNet-O2 / ColecoVision Rev0's)
guide_od = 8.6;  guide_id = 6.4;  guide_h = 2.6;
cap_d   = 4.4;  cap_hole = 4.8;  fl_d = 6.0;  stem_d = 2.6;
tube_od = pin_d + 2.2;               // pin-hole guide tubes
tube_z  = z_f + sw_h + 1.0;          // ... ending 1 mm above the buttons
recess  = 1.2;                       // the pin-holes sit in a counterbore this deep: no accidental press
shroud_z = z_f + 2.0;                // LED shrouds end 2 mm above F.Cu
pilot_top = case_h - 1.4;            // the pilot stops 1.4 mm short of the lid's top

function Y(y) = -y;                  // board y -> case Y
function inside(p, c, wh, m) = abs(p[0] - c[0]) < wh[0] / 2 + m && abs(p[1] - c[1]) < wh[1] / 2 + m;
function boxes_meet(a, b) = a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
function d2(a, b) = norm([a[0] - b[0], a[1] - b[1]]);

pins = [sw_bootsel, sw_s3boot, sw_s3en];
face_holes = concat([[sw_reset, guide_od]], [for (p = pins) [p, tube_od + 2]], [[sw_dip, max(dip_win) + 2]],
                    [for (l = led_win) [l[0], l[1] + 1.6]]);    // [centre, outer diameter]

// the numbers the board and the parts need, checked
assert(top_clr >= parts_max_h + 0.6, "parts too tall for the lid");
assert(under >= 3.0, "no room under the board for the THT leads");
assert(len([for (f = face_holes) if (inside(f[0], label_c, label_wh, f[1] / 2 + 1)) 1]) == 0, "a lid hole in the label");
assert(len([for (h = pcb_holes) if (d2(h, esp32_ant) < 15 + head_d / 2) 1]) == 0, "a screw within 15 mm of the antenna");
assert(hdr_open[0] >= hdr_len + 1.0 && hdr_open[1] >= hdr_h + 0.6, "the west opening does not clear the header's shroud");
assert(d2(sw_reset, sw_bootsel) >= guide_od / 2 + tube_od / 2 + 0.4, "the RESET guide meets the BOOTSEL tube");
echo(str("case: ", case_w, " x ", case_d, " x ", case_h, " mm (W x D x H); B.Cu at z ", z_b, ", F.Cu at z ", z_f,
         " (the parting plane); lid ", top_clr, " mm over F.Cu (tallest part ", parts_max_h, ")"));

// ---------------------------------------------------------------- outline --
module outer2d() { translate([cx0 + r_out, Y(cy1) + r_out]) offset(r = r_out) square([case_w - 2 * r_out, case_d - 2 * r_out]); }
module inner2d() { offset(delta = -wall) outer2d(); }
module lip2d()   { difference() { offset(delta = wall / 2) inner2d(); inner2d(); } }
module board2d() { translate([pcb_x0 + pcb_r, Y(pcb_y1) + pcb_r]) offset(r = pcb_r) square([pcb_x1 - pcb_x0 - 2 * pcb_r, pcb_y1 - pcb_y0 - 2 * pcb_r]); }
module at(p)     { translate([p[0], Y(p[1])]) children(); }
module bosses()  { for (h = pcb_holes) at(h) children(); }

// ------------------------------------------------------------ openings ---
// west: the box header's mouth (its shroud from F.Cu up, centred on the header); the ribbon's IDC socket
// plugs straight in.  north: USB-C (receptacle 8.94 x 3.26, centre 1.63 above F.Cu; the opening takes a
// plug's overmold, up to 12.5 x 7).  south: the microSD's card (11 x 0.8, ~1 mm above F.Cu) and a thumb notch.
module wall_openings() {
    translate([cx0 - eps, Y(hdr_mouth[1]) - hdr_open[0] / 2, z_f - 0.2]) cube([wall + side_clr + 1, hdr_open[0], hdr_open[1] + 0.2]);
    translate([usb_c[0] - 6.5, Y(pcb_y0) - eps, z_f + 1.63 - 3.6]) cube([13, pcb_y0 - cy0 + 2 * eps, 7.2]);
    translate([microsd[0] - 7, Y(cy1) - eps, z_f + 0.2]) cube([14, cy1 - pcb_y1 + 2 * eps, 2.4]);
}
module sd_notch() { translate([microsd[0] - 7, Y(cy1) - eps, z_f + 0.2]) cube([14, cy1 - pcb_y1 + 2 * eps, case_h - z_f]); }

// the lid: RESET through a plunger; BOOTSEL, S3 BOOT and S3 EN through recessed pin-holes in guide tubes;
// a window over the DIP switches; LED windows with shrouds (no light bleeding between them)
module lid_cuts() {
    at(sw_reset) {
        translate([0, 0, z_lin - eps]) cylinder(d = cap_hole, h = wall + 2 * eps);
        translate([0, 0, z_lin - guide_h - eps]) cylinder(d = guide_id, h = guide_h + eps);
    }
    for (p = pins) at(p) {
        translate([0, 0, tube_z - eps]) cylinder(d = pin_d, h = case_h - tube_z + 2 * eps);
        translate([0, 0, case_h - recess]) cylinder(d = pin_d + 2.0, h = recess + eps);
    }
    at(sw_dip) translate([-dip_win[0] / 2, -dip_win[1] / 2, z_lin - eps]) cube([dip_win[0], dip_win[1], wall + 2 * eps]);
    for (l = led_win) at(l[0]) translate([0, 0, (l[2] ? shroud_z : z_lin) - eps]) cylinder(d = l[1], h = case_h - (l[2] ? shroud_z : z_lin) + 2 * eps);
}
module lid_tubes() {
    at(sw_reset) translate([0, 0, z_lin - guide_h]) cylinder(d = guide_od, h = guide_h + eps);
    for (p = pins) at(p) translate([0, 0, tube_z]) cylinder(d = tube_od, h = z_lin - tube_z + eps);
    for (l = led_win) if (l[2]) at(l[0]) translate([0, 0, shroud_z]) cylinder(d = l[1] + 1.6, h = z_lin - shroud_z + eps);
}
module label_recess() {
    if (label_t > 0) translate([label_c[0] - label_wh[0] / 2, Y(label_c[1]) - label_wh[1] / 2, case_h - label_t]) cube([label_wh[0], label_wh[1], label_t + eps]);
}
module lip_seat() { translate([0, 0, z_f - eps]) linear_extrude(lip + 0.2) offset(delta = 0.15) lip2d(); }

// ------------------------------------------------------------------ parts --
module lid() {
    difference() {
        union() {
            translate([0, 0, z_lin]) linear_extrude(wall) outer2d();                             // top plate
            translate([0, 0, z_f]) linear_extrude(case_h - z_f) difference() { outer2d(); inner2d(); }
            bosses() translate([0, 0, z_f]) cylinder(d = boss_d, h = z_lin - z_f + eps);         // press on F.Cu
            lid_tubes();
        }
        bosses() translate([0, 0, z_f - eps]) cylinder(d = insert_d > 0 ? insert_d : pilot_d, h = pilot_top - z_f + eps);
        lid_cuts();
        lip_seat();
        wall_openings();
        sd_notch();
        label_recess();
    }
}

module tray() {
    difference() {
        union() {
            linear_extrude(floor_t) outer2d();                                                  // floor
            linear_extrude(z_f) difference() { outer2d(); inner2d(); }                         // walls to the parting plane
            bosses() cylinder(d = boss_d, h = z_b);                                            // B.Cu rests on them
            translate([0, 0, z_f - eps]) linear_extrude(lip + eps) lip2d();                     // alignment lip
        }
        bosses() {
            translate([0, 0, -eps]) cylinder(d = screw_d, h = z_b + 2 * eps);
            translate([0, 0, -eps]) cylinder(d = head_d, h = head_h + eps);
        }
        wall_openings();
    }
}

// RESET plunger, modelled cap-down (its print orientation): the cap through the 4.8 mm hole, a 45-degree
// cone (no support) into a flange held in the guide, a stem onto the TS-1187A.  At rest the cone sits
// on the hole's edge, the cap `proud` above the lid and the stem `press_gap` above the button.
cap_l    = wall + proud - (cap_hole - cap_d) / 2;
cone_h   = (fl_d - cap_d) / 2;
stem_end = wall + proud + top_clr - sw_h - press_gap;     // from the cap's top
module plunger() {
    cylinder(d = cap_d, h = cap_l + eps);
    translate([0, 0, cap_l]) cylinder(d1 = cap_d, d2 = fl_d, h = cone_h);
    translate([0, 0, cap_l + cone_h - eps]) cylinder(d = fl_d, h = 0.7 + eps);
    translate([0, 0, cap_l + cone_h + 0.7 - eps]) cylinder(d = stem_d, h = stem_end - (cap_l + cone_h + 0.7) + eps);
}
module plunger_fitted(drop = 0) { at(sw_reset) translate([0, 0, case_h + proud - drop]) rotate([180, 0, 0]) plunger(); }

// the board and its parts, for the "assembled" / "section" / "check" views
module board(shrink = 0) { translate([0, 0, z_b + shrink]) linear_extrude(pcb_t - 2 * shrink) offset(delta = -shrink) board2d(); }
module part_boxes(lift = 0) {       // every fitted F.Cu courtyard, extruded to its part's height
    for (p = parts) translate([p[0], Y(p[3]), z_f + 0.01 + lift]) cube([p[2] - p[0], p[3] - p[1], p[4]]);
}
module assembled() {
    color("khaki") tray();
    color("khaki", 0.6) lid();
    color("green") board();
    color("gray") part_boxes();
    color("red") plunger_fitted();
}
// print orientation: the lid turned over about its own middle (a rotation, never a mirror)
module lid_print() { translate([0, Y(cy0) + Y(cy1), case_h]) rotate([180, 0, 0]) lid(); }

// ---------------------------------------------------------------- output --
part = "both";   // "lid", "tray", "plunger", "both" (print layout), "assembled", "section", "check",
                 // "parts_check", "parts_control"
if (part == "lid") lid_print();
else if (part == "tray") tray();
else if (part == "plunger") plunger();
else if (part == "assembled") assembled();
else if (part == "section")      // cut across the header and the RP, seen from the south
    difference() { assembled(); translate([cx0 - 1, Y(78), -1]) cube([case_w + 2, case_d, case_h + 2]); }
else if (part == "check") {      // must be empty: the board and the plunger only touch the case
    intersection() { board(0.05); lid(); }
    intersection() { board(0.05); tray(); }
    intersection() { plunger_fitted(0.05); lid(); }
}
else if (part == "parts_check") {    // must be empty: every part's courtyard box, to its height, clears the case
    intersection() { part_boxes(); lid(); }
    intersection() { part_boxes(); tray(); }
}
else if (part == "parts_control")    // must NOT be empty: the same boxes raised to the lid meet it
    intersection() { part_boxes(top_clr - 1.0); lid(); }
else {
    tray();
    translate([case_w + 10, 0, 0]) lid_print();
    translate([cx1 + case_w + 20, Y(cy1) + 8, 0]) plunger();
}
