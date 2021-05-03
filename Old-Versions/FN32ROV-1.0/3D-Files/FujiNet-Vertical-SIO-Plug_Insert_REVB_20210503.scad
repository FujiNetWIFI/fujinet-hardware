// Fujinet 1.0 plug insert.
// made by Jakub Husak, 2021
// do-what-you-want-ware.

difference(){
    linear_extrude(height=11){
        minkowski(){
        circle($fn=8);
        polygon(points=[[0,0],[1.5,6],[22,6],[23.5,0]]);
        }
    }

    for (i =[0 : 21.5/6 : 21.5])
        translate([i+1, 1.5, 0])
            pin();
    
    for (i =[0:18/5:18])
        translate([i+2.75, 4.5, 0])
            pin();
    
    translate([-2, 4, 8])
        cube([30, 1, 3]);
    translate([-2, 1, 8])
        cube([30, 1, 3]);
    
}

module pin(){
    union()
    {
        cylinder(h=12, $fn=8, r=0.8);
        cylinder(h=1,  $fn=8, r=1);
        }
}