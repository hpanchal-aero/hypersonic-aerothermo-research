// ============================================================
// Project 01 (reset) - Shakedown A mesh.
// Identical O-grid geometry to the prior repository's verified
// Stage 1 (near-body: Nose/Cone/Fillet/Base blocks) + Stage 2
// (structured buffer ring + unstructured far-field) design.
// Mesh geometry does not depend on freestream Mach number - this
// same mesh is reused for production; only the OpenFOAM case's
// freestream BCs and solver startup strategy differ for Shakedown A.
// ============================================================

R_n = 0.05;
theta_c = 15 * Pi/180;
R_b = 0.15;

x_t = R_n * (1 - Sin(theta_c));
r_t = R_n * Cos(theta_c);
L = x_t + (R_b - r_t) / Tan(theta_c);

h0 = 5.607e-6;
ratio = 1.12;
Nwn = 51;
delta_star = h0 * (ratio^Nwn - 1) / (ratio - 1);

nose_off_x = -delta_star;
nose_off_r = 0;

tangent_nx = -Sin(theta_c);
tangent_nr = Cos(theta_c);
tangent_off_x = x_t + delta_star * tangent_nx;
tangent_off_r = r_t + delta_star * tangent_nr;

n1x = -Sin(theta_c); n1r = Cos(theta_c);
n2x = 1;              n2r = 0;
d1x = Cos(theta_c);   d1r = Sin(theta_c);
d2x = 0;              d2r = -1;

r_f = 0.003;

cos_phi = n1x*n2x + n1r*n2r;
cos_half_phi = Sqrt((1 + cos_phi) / 2);
sin_half_phi = Sqrt(1 - cos_half_phi^2);

t_fillet = r_f / cos_half_phi;
tangent_dist = t_fillet * sin_half_phi;

bx = n1x + n2x; br = n1r + n2r;
bmag = Sqrt(bx^2 + br^2);
bx_n = bx / bmag; br_n = br / bmag;

fillet_center_x = L - t_fillet * bx_n;
fillet_center_r = R_b - t_fillet * br_n;

fillet_cone_tan_x = L - tangent_dist * d1x;
fillet_cone_tan_r = R_b - tangent_dist * d1r;

fillet_base_tan_x = L + tangent_dist * d2x;
fillet_base_tan_r = R_b + tangent_dist * d2r;

fillet_cone_tan_off_x = fillet_cone_tan_x + delta_star * n1x;
fillet_cone_tan_off_r = fillet_cone_tan_r + delta_star * n1r;
fillet_base_tan_off_x = fillet_base_tan_x + delta_star * n2x;
fillet_base_tan_off_r = fillet_base_tan_r + delta_star * n2r;

delta_aft = delta_star;
base_axis_ds_x = L + delta_aft;

lc_collar = 0.002;

// ---------------- Points: near-body collar ----------------

p_nose_tip     = newp; Point(p_nose_tip)     = {0,     0,    0, lc_collar};
p_nose_center  = newp; Point(p_nose_center)  = {R_n,   0,    0, lc_collar};
p_tangent      = newp; Point(p_tangent)      = {x_t,   r_t,  0, lc_collar};
p_base_axis    = newp; Point(p_base_axis)    = {L,     0,    0, lc_collar};

p_nose_tip_off = newp; Point(p_nose_tip_off) = {nose_off_x,    nose_off_r,    0, lc_collar};
p_tangent_off  = newp; Point(p_tangent_off)  = {tangent_off_x, tangent_off_r, 0, lc_collar};

p_fillet_cone_tan     = newp; Point(p_fillet_cone_tan)     = {fillet_cone_tan_x,     fillet_cone_tan_r,     0, lc_collar};
p_fillet_base_tan     = newp; Point(p_fillet_base_tan)     = {fillet_base_tan_x,     fillet_base_tan_r,     0, lc_collar};
p_fillet_center       = newp; Point(p_fillet_center)       = {fillet_center_x,       fillet_center_r,       0, lc_collar};
p_fillet_cone_tan_off = newp; Point(p_fillet_cone_tan_off) = {fillet_cone_tan_off_x, fillet_cone_tan_off_r, 0, lc_collar};
p_fillet_base_tan_off = newp; Point(p_fillet_base_tan_off) = {fillet_base_tan_off_x, fillet_base_tan_off_r, 0, lc_collar};

p_base_axis_ds = newp; Point(p_base_axis_ds) = {base_axis_ds_x, 0, 0, lc_collar};

// ---------------- Curves: near-body collar ----------------

N1 = newl; Circle(N1) = {p_nose_tip, p_nose_center, p_tangent};
N2 = newl; Line(N2)   = {p_tangent, p_tangent_off};
N3 = newl; Line(N3)   = {p_nose_tip_off, p_tangent_off};
N4 = newl; Line(N4)   = {p_nose_tip, p_nose_tip_off};

C1 = newl; Line(C1) = {p_tangent, p_fillet_cone_tan};
C2 = newl; Line(C2) = {p_fillet_cone_tan, p_fillet_cone_tan_off};
C3 = newl; Line(C3) = {p_tangent_off, p_fillet_cone_tan_off};

F1 = newl; Circle(F1) = {p_fillet_cone_tan, p_fillet_center, p_fillet_base_tan};
F2 = newl; Line(F2)   = {p_fillet_base_tan, p_fillet_base_tan_off};
F3 = newl; Line(F3)   = {p_fillet_cone_tan_off, p_fillet_base_tan_off};

Bs1 = newl; Line(Bs1) = {p_fillet_base_tan, p_base_axis};
Bs2 = newl; Line(Bs2) = {p_base_axis, p_base_axis_ds};
Bs3 = newl; Line(Bs3) = {p_base_axis_ds, p_fillet_base_tan_off};

// ---------------- Surfaces: near-body ----------------

LoopN = newll; Curve Loop(LoopN) = {N1, N2, -N3, -N4};
SurfN = news;  Plane Surface(SurfN) = {LoopN};

LoopC = newll; Curve Loop(LoopC) = {C1, C2, -C3, -N2};
SurfC = news;  Plane Surface(SurfC) = {LoopC};

LoopF = newll; Curve Loop(LoopF) = {F1, F2, -F3, -C2};
SurfF = news;  Plane Surface(SurfF) = {LoopF};

LoopBs = newll; Curve Loop(LoopBs) = {Bs1, Bs2, Bs3, -F2};
SurfBs = news;  Plane Surface(SurfBs) = {LoopBs};

// ---------------- Transfinite: near-body ----------------

Transfinite Curve{N1} = 61 Using Progression 1;
Transfinite Curve{N3} = 61 Using Progression 1;
Transfinite Curve{N2} = 52 Using Progression ratio;
Transfinite Curve{N4} = 52 Using Progression ratio;
Transfinite Surface{SurfN} = {p_nose_tip, p_tangent, p_tangent_off, p_nose_tip_off};
Recombine Surface{SurfN};

Transfinite Curve{C1} = 151 Using Progression 1;
Transfinite Curve{C3} = 151 Using Progression 1;
Transfinite Curve{C2} = 52 Using Progression ratio;
Transfinite Surface{SurfC} = {p_tangent, p_fillet_cone_tan, p_fillet_cone_tan_off, p_tangent_off};
Recombine Surface{SurfC};

Transfinite Curve{F1} = 15 Using Progression 1;
Transfinite Curve{F3} = 15 Using Progression 1;
Transfinite Curve{F2} = 52 Using Progression ratio;
Transfinite Surface{SurfF} = {p_fillet_cone_tan, p_fillet_base_tan, p_fillet_base_tan_off, p_fillet_cone_tan_off};
Recombine Surface{SurfF};

Transfinite Curve{Bs1} = 76 Using Progression 1;
Transfinite Curve{Bs3} = 76 Using Progression 1;
Transfinite Curve{Bs2} = 52 Using Progression ratio;
Transfinite Surface{SurfBs} = {p_fillet_base_tan, p_base_axis, p_base_axis_ds, p_fillet_base_tan_off};
Recombine Surface{SurfBs};

// ============================================================
// Buffer ring
// ============================================================

t_buf  = 0.018;
margin = 0.020;
buffer_ratio = 1.091986;
Nbufdiv = 9;

p_nose_tip_off_buf = newp; Point(p_nose_tip_off_buf) = {nose_off_x - t_buf, 0, 0, lc_collar};

p_tangent_off_buf = newp; Point(p_tangent_off_buf) = {
  tangent_off_x + t_buf*tangent_nx,
  tangent_off_r + t_buf*tangent_nr,
  0, lc_collar};

p_fillet_cone_tan_off_buf = newp; Point(p_fillet_cone_tan_off_buf) = {
  fillet_cone_tan_off_x + t_buf*n1x,
  fillet_cone_tan_off_r + t_buf*n1r,
  0, lc_collar};

p_fillet_base_tan_off_buf = newp; Point(p_fillet_base_tan_off_buf) = {
  fillet_base_tan_off_x + t_buf*n2x,
  fillet_base_tan_off_r + t_buf*n2r,
  0, lc_collar};

p_base_axis_ds_buf = newp; Point(p_base_axis_ds_buf) = {base_axis_ds_x + t_buf, 0, 0, lc_collar};

NbufAxis  = newl; Line(NbufAxis)  = {p_nose_tip_off, p_nose_tip_off_buf};
BufSpoke1 = newl; Line(BufSpoke1) = {p_tangent_off, p_tangent_off_buf};
BufSpoke2 = newl; Line(BufSpoke2) = {p_fillet_cone_tan_off, p_fillet_cone_tan_off_buf};
BufSpoke3 = newl; Line(BufSpoke3) = {p_fillet_base_tan_off, p_fillet_base_tan_off_buf};
BsbufAxis = newl; Line(BsbufAxis) = {p_base_axis_ds, p_base_axis_ds_buf};

NbufOuter  = newl; Line(NbufOuter)  = {p_nose_tip_off_buf, p_tangent_off_buf};
CbufOuter  = newl; Line(CbufOuter)  = {p_tangent_off_buf, p_fillet_cone_tan_off_buf};
FbufOuter  = newl; Line(FbufOuter)  = {p_fillet_cone_tan_off_buf, p_fillet_base_tan_off_buf};
BsbufOuter = newl; Line(BsbufOuter) = {p_fillet_base_tan_off_buf, p_base_axis_ds_buf};

LoopNbuf = newll; Curve Loop(LoopNbuf) = {N3, BufSpoke1, -NbufOuter, -NbufAxis};
SurfNbuf = news;  Plane Surface(SurfNbuf) = {LoopNbuf};

LoopCbuf = newll; Curve Loop(LoopCbuf) = {C3, BufSpoke2, -CbufOuter, -BufSpoke1};
SurfCbuf = news;  Plane Surface(SurfCbuf) = {LoopCbuf};

LoopFbuf = newll; Curve Loop(LoopFbuf) = {F3, BufSpoke3, -FbufOuter, -BufSpoke2};
SurfFbuf = news;  Plane Surface(SurfFbuf) = {LoopFbuf};

LoopBsbuf = newll; Curve Loop(LoopBsbuf) = {-Bs3, BsbufAxis, -BsbufOuter, -BufSpoke3};
SurfBsbuf = news;  Plane Surface(SurfBsbuf) = {LoopBsbuf};

Transfinite Curve{NbufOuter}  = 61  Using Progression 1;
Transfinite Curve{CbufOuter}  = 151 Using Progression 1;
Transfinite Curve{FbufOuter}  = 15  Using Progression 1;
Transfinite Curve{BsbufOuter} = 76  Using Progression 1;

Transfinite Curve{NbufAxis}  = Nbufdiv Using Progression buffer_ratio;
Transfinite Curve{BufSpoke1} = Nbufdiv Using Progression buffer_ratio;
Transfinite Curve{BufSpoke2} = Nbufdiv Using Progression buffer_ratio;
Transfinite Curve{BufSpoke3} = Nbufdiv Using Progression buffer_ratio;
Transfinite Curve{BsbufAxis} = Nbufdiv Using Progression buffer_ratio;

Transfinite Surface{SurfNbuf}  = {p_nose_tip_off, p_tangent_off, p_tangent_off_buf, p_nose_tip_off_buf};
Recombine Surface{SurfNbuf};

Transfinite Surface{SurfCbuf}  = {p_tangent_off, p_fillet_cone_tan_off, p_fillet_cone_tan_off_buf, p_tangent_off_buf};
Recombine Surface{SurfCbuf};

Transfinite Surface{SurfFbuf}  = {p_fillet_cone_tan_off, p_fillet_base_tan_off, p_fillet_base_tan_off_buf, p_fillet_cone_tan_off_buf};
Recombine Surface{SurfFbuf};

Transfinite Surface{SurfBsbuf} = {p_fillet_base_tan_off, p_base_axis_ds, p_base_axis_ds_buf, p_fillet_base_tan_off_buf};
Recombine Surface{SurfBsbuf};

// ============================================================
// Unstructured far-field
// ============================================================

x_upstream = -6 * R_n;
r_outer    = 15 * R_n;
x_outlet   = base_axis_ds_x + t_buf + margin;

lc_far = 0.04;

p_axis_up     = newp; Point(p_axis_up)     = {x_upstream, 0,       0, lc_far};
p_farfield_up = newp; Point(p_farfield_up) = {x_upstream, r_outer, 0, lc_far};
p_outlet_top  = newp; Point(p_outlet_top)  = {x_outlet,   r_outer, 0, lc_far};
p_outlet_axis = newp; Point(p_outlet_axis) = {x_outlet,   0,       0, lc_far};

FarOut1 = newl; Line(FarOut1) = {p_axis_up, p_nose_tip_off_buf};
FarOut2 = newl; Line(FarOut2) = {p_base_axis_ds_buf, p_outlet_axis};
FarOut3 = newl; Line(FarOut3) = {p_outlet_axis, p_outlet_top};
FarOut4 = newl; Line(FarOut4) = {p_outlet_top, p_farfield_up};
FarOut5 = newl; Line(FarOut5) = {p_farfield_up, p_axis_up};

LoopFarfield = newll;
Curve Loop(LoopFarfield) = {FarOut1, NbufOuter, CbufOuter, FbufOuter, BsbufOuter, FarOut2, FarOut3, FarOut4, FarOut5};
SurfFarfield = news; Plane Surface(SurfFarfield) = {LoopFarfield};

Field[1] = Distance;
Field[1].CurvesList = {NbufOuter, CbufOuter, FbufOuter, BsbufOuter};
Field[1].Sampling = 200;

Field[2] = Threshold;
Field[2].InField = 1;
Field[2].SizeMin = 4.5e-3;
Field[2].SizeMax = 0.04;
Field[2].DistMin = 0;
Field[2].DistMax = 0.4;

Background Field = 2;
Mesh.CharacteristicLengthFromPoints = 0;
Mesh.CharacteristicLengthExtendFromBoundary = 0;

Mesh.Algorithm = 6;

// ============================================================
// WEDGE EXTRUSION
// ============================================================
half_angle = 1 * Pi/180;
full_angle = 2 * half_angle;

Rotate { {1,0,0}, {0,0,0}, -half_angle } {
  Surface{SurfN, SurfC, SurfF, SurfBs, SurfNbuf, SurfCbuf, SurfFbuf, SurfBsbuf, SurfFarfield};
}

outN[]        = Extrude { {1,0,0}, {0,0,0}, full_angle } { Surface{SurfN};        Layers{1}; Recombine; };
outC[]        = Extrude { {1,0,0}, {0,0,0}, full_angle } { Surface{SurfC};        Layers{1}; Recombine; };
outF[]        = Extrude { {1,0,0}, {0,0,0}, full_angle } { Surface{SurfF};        Layers{1}; Recombine; };
outBs[]       = Extrude { {1,0,0}, {0,0,0}, full_angle } { Surface{SurfBs};       Layers{1}; Recombine; };
outNbuf[]     = Extrude { {1,0,0}, {0,0,0}, full_angle } { Surface{SurfNbuf};     Layers{1}; Recombine; };
outCbuf[]     = Extrude { {1,0,0}, {0,0,0}, full_angle } { Surface{SurfCbuf};     Layers{1}; Recombine; };
outFbuf[]     = Extrude { {1,0,0}, {0,0,0}, full_angle } { Surface{SurfFbuf};     Layers{1}; Recombine; };
outBsbuf[]    = Extrude { {1,0,0}, {0,0,0}, full_angle } { Surface{SurfBsbuf};    Layers{1}; Recombine; };
outFarfield[] = Extrude { {1,0,0}, {0,0,0}, full_angle } { Surface{SurfFarfield}; Layers{1}; Recombine; };

// Indices confirmed via BoundingBox diagnostic in the prior repository's
// Stage 2 verification: outlet=outFarfield[6], farfield_outer=outFarfield[7],
// farfield_upstream=outFarfield[8]

Physical Surface("frontWedge") = {SurfN, SurfC, SurfF, SurfBs, SurfNbuf, SurfCbuf, SurfFbuf, SurfBsbuf, SurfFarfield};
Physical Surface("backWedge")  = {outN[0], outC[0], outF[0], outBs[0], outNbuf[0], outCbuf[0], outFbuf[0], outBsbuf[0], outFarfield[0]};

Physical Surface("wall_nose")   = {outN[2]};
Physical Surface("wall_cone")   = {outC[2]};
Physical Surface("wall_fillet") = {outF[2]};
Physical Surface("wall_base")   = {outBs[2]};

Physical Surface("outlet")            = {outFarfield[6]};
Physical Surface("farfield_outer")    = {outFarfield[7]};
Physical Surface("farfield_upstream") = {outFarfield[8]};

Physical Volume("internal") = {outN[1], outC[1], outF[1], outBs[1], outNbuf[1], outCbuf[1], outFbuf[1], outBsbuf[1], outFarfield[1]};

Mesh.Optimize = 0;
Mesh.OptimizeNetgen = 0;
Mesh.Smoothing = 0;
