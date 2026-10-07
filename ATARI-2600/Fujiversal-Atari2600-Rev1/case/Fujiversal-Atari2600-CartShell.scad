// Fujiversal-Atari2600 Rev1 -- full-size cartridge shell
// ---------------------------------------------------------------------------
// A re-model of "Atari 2600 Cartridge Shell - Easy Print" by norm8332
// (https://www.thingiverse.com/thing:1790785, Creative Commons Attribution),
// adapted to carry the Rev1 board.  The shell geometry (outline, walls,
// floors, fillets, screw bosses, countersinks, holder channel, end-label
// recess, holder) was measured from norm8332's REV_3 top/bott and REV_2
// holder STLs and redrawn here; it is not an import of those meshes.
// Changes from the original:
//   * norm8332's PCB ribs (rear half) and clamp posts (front half) removed:
//     they sit inside the Rev1 footprint;
//   * Rev1 retention: four rear standoffs with locating pins into the board's
//     3.2 mm NPTH holes, four front posts on the label face;
//   * openings: USB-C in the top end, microSD slot + guide tunnel in the
//     right side, RESET flexure button, BOOTSEL / S3 EN / S3 BOOT pin-holes
//     and two LED light holes in the rear face;
//   * optional lengthening (`stretch`) for a deeper edge recess;
//   * holder slot centred on the Rev1 board plane, grip nubs on both faces.
//
// Unlike Fujiversal-Atari2600-Shell.scad (a clamshell over the board's top
// only), this is a whole cartridge: the board's tab sits inside the open
// bottom end like any 2600 cart and the body goes into the slot.
//
// Coordinate frame = the KiCad board frame, as in Fujiversal-Atari2600-Shell.scad:
//   X = board x, Y = -(board y) (+Y toward the cart's top end),
//   Z = 0 at the outside of the FRONT (label, B.Cu) half, +Z toward the
//   console rear.  The REAR half carries the screws and faces F.Cu.
// norm8332's measurements are written in cart coordinates (u, v, w):
//   u across the cart from its left side, v up from the open (bottom) end,
//   w into a half from its outside face.
//
//   VERIFY before printing:
//   * edge_recess: measure an original Atari cart from the bottom face of the
//     shell to the tips of the PCB fingers.  Err low: an edge recessed too
//     deep keeps the fingers from seating.  Above 7.3 mm the shell lengthens.
//
// Print: all parts outside-down, no supports, 0.2 mm layers, PETG or PLA.
// Assemble with four countersunk wood screws (#4 x 1/2", or M2.5-M3 x 12
// self-tapping) from the rear face.

include <board-anchors.scad>

// --------------------------------------------------- board in the cart --
edge_recess = 6.5;    // VERIFY: open end of the shell -> contact edge (mm)
pcb_t   = 1.6;
top_clr = 0.3;        // board top edge -> inside of the end wall, minimum

// ------------------------------------------ norm8332 geometry (measured) --
cw      = 81.49;      // outside width
ch0     = 98.0;       // outside height (unstretched)
T       = 20.22;      // assembled thickness
rim_f   = 11.08;      // front half: outside face -> parting plane
rim_r   = T - rim_f;  // rear half (9.14)
wall    = 2.6;        // side walls
corner_r = 1.2;       // vertical corners
face_r  = 3.0;        // fillet along the long edges of both outside faces
floor_t = 1.94;
floor_mouth = 1.44;   // floor next to the open end ...
mouth_v = 22.2;       // ... below this v
end_in  = 95.6;       // inside face of the top end wall
label_v = 97.2;       // end-label recess: v from here to the top, 0.8 deep,
label_u = 4.75;       //   u from label_u to cw - label_u,
label_w = [2.51, 2.61]; //  w above these (front, rear)
// holder channel: two ridges across the floor, extended up the side walls
ridge_v = [[22.2, 23.6], [26.2, 27.6]];
ridge_w = [3.46, 2.54];   // ridge tops (front, rear), from the outside face
chan_floor = [1.94, 2.04];
ridge_block = 1.4;        // ridge ends thicken the side walls this much
// screw bosses (u, v centres)
boss_r  = 3.6;
bosses  = [[6.8, 34.1], [cw - 6.8, 34.1], [6.8, 93.1], [cw - 6.8, 93.1]];
boss_f_h = 10.58;         // front bosses stop 0.5 under the parting plane
hole_d  = 3.5;            // rear clearance hole
csk_d   = 6.9;            // countersink on the rear face
csk_h   = 2.5;
pilot_d = 2.5;            // front pilot
// holder (bulkhead in the channel between the ridges)
hold_t  = 1.98;
hold_slot_l = 56.2;
hold_slot_w = 2.4;
hold_gap = 1.8;           // between the grip nubs
hold_nub_x = 12.2;        // nub centres either side of the slot centre
hold_nub_l = 2.6;
hold_post_l = 16.13;      // posts run from the plate toward the open end
hold_post_w = 5.2;
hold_post_t = 2.2;
hold_clr = 0.15;

// ------------------------------------------------- Rev1 retention + I/O --
standoff_d = 4.6;     // rear, from the floor to F.Cu (clears the parts round each hole)
pin_d   = 2.9;        // into the 3.2 mm NPTH
pin_h   = 1.4;
post_d  = 6.0;        // front, from the floor to B.Cu
crush   = 0.1;        // front posts press the board this much
usb_mouth = [13, 7.2];        // plug overmold
usb_axis  = 1.63;             // receptacle axis behind F.Cu
sd_card   = [0.55, 1.35];     // card faces above F.Cu inside the TF-015
sd_w      = 11.8;             // tunnel width (card 11)
sd_rail   = 1.1;
sw_top    = 1.54;             // TL3342F160QG actuator above F.Cu
flex_w    = 6;  flex_free = 2.5; flex_hinge = 5.5;  // RESET tongue round sw_reset
flex_cut  = 0.8;
flex_t    = 1.2;
nub_d     = 3.0;

$fn = 40;
eps = 0.01;

// ----------------------------------------------------------- derived ----
stretch = max(0, edge_recess + (board[3] - board[1]) + top_clr - end_in);
ch   = ch0 + stretch;
X0   = (board[0] + board[2]) / 2 - cw / 2;   // cart left side (the tab is centred)
Yo   = -(board[3] + edge_recess);             // cart open end
z_b  = 11.25;                                 // board B.Cu face (norm8332's board plane)
z_f  = z_b + pcb_t;                           // F.Cu face (12.85)
z_mid = z_b + pcb_t / 2;
z_ff = floor_t;                               // inside of the front floor
z_rf = T - floor_t;                           // inside of the rear floor
function V(v) = v > 60 ? v + stretch : v;     // norm8332 v -> stretched v
function Y(y) = -y;                           // board y -> shell Y
x_wall_r = X0 + cw - wall;                    // inside face of the right wall
hold_v = (ridge_v[0][1] + ridge_v[1][0]) / 2; // plate centre
sd_z  = [z_f + sd_card[0], z_f + sd_card[1]];

echo(str("cart shell: ", cw, " x ", ch, " x ", T, " mm, stretch ", stretch,
         "; edge recess ", edge_recess, "; board top ", Yo + V(end_in) - Y(board[1]),
         " mm under the end wall; F.Cu -> rear floor ", z_rf - z_f,
         "; board side gaps ", board[0] - (X0 + wall), " / ", x_wall_r - board[2]));

// Rev1 outline (Edge.Cuts): full width above shoulder_y, 45-degree shoulders,
// 32.4 mm tab with 1 mm chamfers
tab_x = [83.8, 116.2];
tab_y = 102.44;
module board2d() {
    polygon([[board[0], Y(board[1])], [board[2], Y(board[1])], [board[2], Y(shoulder_y)],
             [tab_x[1], Y(tab_y)], [tab_x[1], Y(board[3] - 1)], [tab_x[1] - 1, Y(board[3])],
             [tab_x[0] + 1, Y(board[3])], [tab_x[0], Y(board[3] - 1)], [tab_x[0], Y(tab_y)],
             [board[0], Y(shoulder_y)]]);
}

// ===================================================== one shell half ====
// Built in cart coordinates (u, v, w); `rim` = parting-plane depth, `k` = 0 front, 1 rear.
module rounded_rect(w, h, r) { offset(r) offset(-r) square([w, h]); }

module half_outer(rim) {
    intersection() {
        linear_extrude(rim) rounded_rect(cw, ch, corner_r);
        // fillet along the long edges of the outside face
        rotate([90, 0, 0]) translate([0, 0, -ch - eps]) linear_extrude(ch + 2 * eps)
            hull() {
                translate([face_r, face_r]) circle(face_r);
                translate([cw - face_r, face_r]) circle(face_r);
                translate([0, rim - eps]) square([cw, eps]);
            }
    }
}

module cavity(rim) {
    // lead-in at the open end: the inside of each wall flares from 1.9 to wall
    lead = [[1.9, -eps], [cw - 1.9, -eps], [cw - wall, 2.5], [cw - wall, mouth_v],
            [wall, mouth_v], [wall, 2.5]];
    translate([0, 0, floor_mouth]) linear_extrude(rim) polygon(lead);
    translate([wall, mouth_v - eps, floor_t]) cube([cw - 2 * wall, V(end_in) - mouth_v + eps, rim]);
}

module boss2d(c, k) {
    left  = c[0] < cw / 2;
    uw    = left ? 0 : cw - wall;            // side-wall strip the boss merges into
    v0    = V(k == 0 ? 86.0 : 88.6);         // top bosses: fillet down the side wall from here
    ue    = k == 0 ? 13.8 : 12.0;            // ... and along the end wall this far (front: gusset)
    reach = k == 0 ? 4.7 : 4.1;              // lower bosses: fillet half-length on the wall
    hull() {
        translate(c) circle(boss_r);
        if (c[1] > 60) {
            translate([uw, v0]) square([wall, V(end_in) - v0]);
            translate([left ? 0 : cw - ue, V(end_in) - eps]) square([ue, eps]);
        } else
            translate([uw, c[1] - reach]) square([wall, 2 * reach]);
    }
}

module half(k) {
    rim = k == 0 ? rim_f : rim_r;
    bc = [for (b = bosses) [b[0], V(b[1])]];
    difference() {
        intersection() {     // everything stays inside the filleted outer body
        union() {
            difference() { half_outer(rim); cavity(rim); }
            // small detent ridge on each wall just inside the mouth
            for (m = [0, 1]) translate([m * cw, 0, 0]) mirror([m, 0, 0])
                linear_extrude(rim) polygon([[wall - eps, 3.2], [3.0, 4.4], [3.0, 6.2], [wall - eps, 6.8]]);
            // holder channel: ridges across the floor, blocks up the walls
            for (r = ridge_v) {
                translate([wall - eps, r[0], 0]) cube([cw - 2 * wall + 2 * eps, r[1] - r[0], ridge_w[k]]);
                for (m = [0, 1]) translate([m * cw, 0, 0]) mirror([m, 0, 0])
                    translate([wall - eps, r[0], 0]) cube([ridge_block + eps, r[1] - r[0], rim]);
            }
            translate([wall - eps, ridge_v[0][1] - eps, 0])
                cube([cw - 2 * wall + 2 * eps, ridge_v[1][0] - ridge_v[0][1] + 2 * eps, chan_floor[k]]);
            // screw bosses
            for (c = bc) linear_extrude(k == 0 ? boss_f_h : rim) boss2d(c, k);
        }
        half_outer(rim);
        }
        // end-label recess
        translate([label_u, V(label_v), label_w[k]]) cube([cw - 2 * label_u, ch - V(label_v) + eps, rim]);
        // screw holes
        for (c = bc) translate([c[0], c[1], 0]) {
            if (k == 1) {
                translate([0, 0, -eps]) cylinder(d = hole_d, h = rim + 2 * eps);
                translate([0, 0, -eps]) cylinder(d1 = csk_d + 2 * eps, d2 = hole_d, h = csk_h + eps);
            } else
                translate([0, 0, floor_t]) cylinder(d = pilot_d, h = boss_f_h);
        }
    }
}

// place a half in the assembled frame
module front_shell() { translate([X0, Yo, 0]) half(0); }
module rear_shell()  { translate([X0, Yo, T]) mirror([0, 0, 1]) half(1); }

// ====================================================== Rev1 features ====
module at_holes() { for (h = holes) translate([h[0], Y(h[1])]) children(); }

module sd_tunnel_front() {   // card shelf with side rails, standing on the front floor
    x0 = board[2] + 0.3;
    translate([0, Y(sd_y), 0]) difference() {
        union() {
            translate([x0, -sd_w / 2 - sd_rail, z_ff - eps]) cube([x_wall_r - x0 + eps, sd_w + 2 * sd_rail, rim_f - z_ff + eps]);
            translate([x0, -sd_w / 2 - sd_rail, rim_f - eps]) cube([x_wall_r - 0.2 - x0, sd_w + 2 * sd_rail, sd_z[1] - 0.3 - rim_f]);
        }
        translate([x0 - eps, -sd_w / 2, sd_z[0] - 0.2]) cube([x_wall_r - x0 + 1, sd_w, 10]);
    }
}

module sd_tunnel_rear() {    // ceiling hanging from the rear floor
    x0 = board[2] + 0.3;
    translate([x0, Y(sd_y) - sd_w / 2 - sd_rail, sd_z[1] + 0.4])
        cube([x_wall_r - x0 + eps, sd_w + 2 * sd_rail, z_rf - (sd_z[1] + 0.4) + eps]);
}

module sd_slot() {           // through the right wall, funnelled outward
    hull() {
        translate([x_wall_r - eps, Y(sd_y) - sd_w / 2, sd_z[0] - 0.2]) cube([eps, sd_w, sd_z[1] - sd_z[0] + 0.6]);
        translate([X0 + cw, Y(sd_y) - sd_w / 2 - 0.9, sd_z[0] - 0.7]) cube([eps, sd_w + 1.8, sd_z[1] - sd_z[0] + 1.6]);
    }
}

module usb_mouth() {
    zc = z_f + usb_axis;
    translate([usb_x - usb_mouth[0] / 2, Yo + V(end_in) - eps, zc - usb_mouth[1] / 2])
        cube([usb_mouth[0], ch - V(end_in) + 2 * eps, usb_mouth[1]]);
}

module reset_flexure_cut() {  // U-cut through the rear floor + the tongue thinned from inside
    x = sw_reset[0]; y = Y(sw_reset[1]);
    y0 = y - flex_hinge; y1 = y + flex_free;
    translate([0, 0, z_rf - eps]) linear_extrude(floor_t + 2 * eps) difference() {
        translate([x - flex_w / 2 - flex_cut, y0]) square([flex_w + 2 * flex_cut, y1 - y0 + flex_cut]);
        translate([x - flex_w / 2, y0 - eps]) square([flex_w, y1 - y0 + eps]);
    }
    translate([x - flex_w / 2, y0 - eps, z_rf - eps]) cube([flex_w, y1 - y0 + eps, floor_t - flex_t + eps]);
}

module rear_holes() {
    for (p = [[sw_bootsel, 2.2], [sw_s3rst, 2.2], [sw_s3boot, 2.2], [ws_led, 3.0], [rp_led, 2.0]])
        translate([p[0][0], Y(p[0][1]), z_rf - eps]) cylinder(d = p[1], h = floor_t + 2 * eps);
    reset_flexure_cut();
}

// ------------------------------------------------------------- halves --
module front_half() {
    difference() {
        union() {
            front_shell();
            at_holes() translate([0, 0, z_ff - eps]) cylinder(d = post_d, h = z_b + crush - z_ff + eps);
            sd_tunnel_front();
        }
        usb_mouth();
    }
}

module rear_half() {
    difference() {
        union() {
            rear_shell();
            at_holes() translate([0, 0, z_f]) cylinder(d = standoff_d, h = z_rf - z_f + eps);
            at_holes() translate([0, 0, z_f - pin_h]) cylinder(d = pin_d, h = pin_h + eps);
            sd_tunnel_rear();
        }
        usb_mouth();
        sd_slot();
        rear_holes();
    }
    // RESET nub on the (thinned) flexure tongue, down to just above the actuator
    translate([sw_reset[0], Y(sw_reset[1]), z_f + sw_top + 0.2])
        cylinder(d = nub_d, h = T - flex_t - (z_f + sw_top + 0.2) + eps);
}

// ------------------------------------------------------------- holder --
// A bulkhead in the channel 24 mm up from the open end.  The board passes
// through its slot; the two posts run toward the open end beside the console's connector.
module holder() {
    lw = cw - 2 * wall - 2 * hold_clr;                  // plate width
    z0 = chan_floor[0] + hold_clr;                      // front channel floor
    z1 = T - chan_floor[1] - hold_clr;                  // rear channel floor
    yp = Yo + hold_v - hold_t / 2;                      // plate face toward the open end
    xc = X0 + cw / 2;
    difference() {
        union() {
            translate([xc - lw / 2, yp, z0]) rotate([-90, 0, 0]) translate([0, -(z1 - z0), 0])
                linear_extrude(hold_t) rounded_rect(lw, z1 - z0, 1);
            for (m = [0, 1]) translate([xc, 0, 0]) mirror([m, 0, 0]) translate([-xc, 0, 0])
                translate([0, 0, z_mid - hold_post_t / 2]) linear_extrude(hold_post_t) {
                    xi = xc - hold_slot_l / 2 - 0.2;
                    xo = xi - hold_post_w;
                    polygon([[xi, yp + eps], [xo, yp + eps], [xo, yp - 9.6],
                             [xo + 1.9, yp - hold_post_l], [xi, yp - hold_post_l]]);
                }
        }
        translate([xc - hold_slot_l / 2, yp - eps, z_mid - hold_slot_w / 2])
            cube([hold_slot_l, hold_t + 2 * eps, hold_slot_w]);
    }
    // grip nubs on both faces of the slot: hold_gap centred on the board
    for (s = [-1, 1]) for (zz = [z_mid - hold_slot_w / 2, z_mid + hold_gap / 2])
        translate([xc + s * hold_nub_x - hold_nub_l / 2, yp, zz]) cube([hold_nub_l, hold_t, (hold_slot_w - hold_gap) / 2]);
}

// ----------------------------------------------- interference check --
// The board slab and a 3.3 mm part envelope on F.Cu (the switches only up to
// their actuators).  The contacts that are meant to touch (the standoff and
// post faces round each hole) are cut out.
module board_keepout() {
    sw = [sw_reset, sw_bootsel, sw_s3rst, sw_s3boot];
    translate([0, 0, z_b]) linear_extrude(pcb_t) difference() {
        board2d();
        at_holes() circle(d = post_d + 0.2);   // (+0.4 would be tangent to the edge at H1)
    }
    translate([0, 0, z_f - eps]) linear_extrude(3.3) difference() {
        intersection() { board2d(); translate([0, Y(90.5)]) square([300, 200]); }
        at_holes() circle(d = standoff_d + 0.2);
        for (s = sw) translate([s[0], Y(s[1])]) square(5.2, center = true);
    }
    for (s = sw) translate([s[0], Y(s[1]), z_f - eps]) linear_extrude(sw_top + 0.1) square(5.2, center = true);
}

// ---------------------------------------------------------------- output --
part = "both";   // "front", "rear", "holder", "both" (print layout), "assembled", "check"
module rear_print()   { translate([0, 0, T]) mirror([0, 0, 1]) rear_half(); }
module holder_print() { translate([0, 0, Yo + hold_v + hold_t / 2]) rotate([-90, 0, 0]) holder(); }
if (part == "front") front_half();
else if (part == "rear") rear_print();
else if (part == "holder") holder_print();
else if (part == "assembled") {
    front_half(); rear_half(); holder();
    %translate([0, 0, z_b]) linear_extrude(pcb_t) board2d();
}
else if (part == "check")
    intersection() { union() { front_half(); rear_half(); holder(); } board_keepout(); }
else {
    front_half();
    translate([90, 0, 0]) rear_print();
    translate([0, 5, 0]) holder_print();         // beyond the top end
}
