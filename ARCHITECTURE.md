# FreeCAD Magic Cube Animation Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    FreeCAD Magic Cube                       │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Spider     │    │  Cubelets    │    │    Legs      │ │
│  │   Frame      │◄───┤  (26 total)  │◄───┤ (8 corners)  │ │
│  │  (3 rods)    │    │              │    │  Telescoping │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Cube Structure (3x3x3)

```
      +Z (Front/Back)
       │
       │   LUB ───── UB ───── RUB
       │    ╱│        │        │╱
       │   ╱ │        │        │
       │  LU ─┼───── Center_U ─┼─ RU
       │  │  LUF ─── UF ───── RUF
       │  │   │       │        │
       │  │   │       │        │
+Y ────┼──┼───┼───── Center ───┼───────►  +X (Right/Left)
(Up/   │  │   │       │        │
Down)  │  │   │       │        │
       │  │  LDF ─── DF ───── RDF
       │  LD ─┼───── Center_D ─┼─ RD
       │   ╲ │        │        │
       │    ╲│        │        │╲
       │   LDB ───── DB ───── RDB
       │
       ▼

Legend:
  R = Right, L = Left
  U = Up, D = Down
  F = Front, B = Back
```

## Face Rotation Groups

Each face contains 9 cubelets:
- 1 center (stays in place but rotates)
- 4 edges
- 4 corners

### Right Face (R) - Rotation around X-axis
```
Cubelets: Center_R, Edge_RU, Edge_RD, Edge_RF, Edge_RB,
          Corner_RUF, Corner_RUB, Corner_RDF, Corner_RDB
```

### Left Face (L) - Rotation around X-axis
```
Cubelets: Center_L, Edge_LU, Edge_LD, Edge_LF, Edge_LB,
          Corner_LUF, Corner_LUB, Corner_LDF, Corner_LDB
```

### Up Face (U) - Rotation around Y-axis
```
Cubelets: Center_U, Edge_RU, Edge_LU, Edge_UF, Edge_UB,
          Corner_RUF, Corner_RUB, Corner_LUF, Corner_LUB
```

### Down Face (D) - Rotation around Y-axis
```
Cubelets: Center_D, Edge_RD, Edge_LD, Edge_DF, Edge_DB,
          Corner_RDF, Corner_RDB, Corner_LDF, Corner_LDB
```

### Front Face (F) - Rotation around Z-axis
```
Cubelets: Center_F, Edge_RF, Edge_LF, Edge_UF, Edge_DF,
          Corner_RUF, Corner_RDF, Corner_LUF, Corner_LDF
```

### Back Face (B) - Rotation around Z-axis
```
Cubelets: Center_B, Edge_RB, Edge_LB, Edge_UB, Edge_DB,
          Corner_RUB, Corner_RDB, Corner_LUB, Corner_LDB
```

## Animation Flow

```
┌──────────────────┐
│  Start Animation │
└────────┬─────────┘
         │
         ▼
┌──────────────────────┐
│ Select Random Face   │
│ (R, L, U, D, F, B)   │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Select Random Dir.   │
│ (+90° or -90°)       │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Get Face Cubelets    │
│ (9 cubelets)         │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Get Rotation Axis    │
│ and Center Point     │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Animate Rotation     │◄────┐
│ (15-20 steps)        │     │
└────────┬─────────────┘     │
         │                   │
         ▼                   │
┌──────────────────────┐     │
│ Each Step:           │     │
│ 1. Translate to 0    │     │
│ 2. Rotate by step    │     │
│ 3. Translate back    │     │
│ 4. Update display    │     │
│ 5. Delay 30ms        │     │
└────────┬─────────────┘     │
         │                   │
         │ More steps? ──────┘
         │
         ▼
┌──────────────────────┐
│ Pause 200ms          │
└────────┬─────────────┘
         │
         │ More moves?
         │
         ├─ Yes ─────────────┐
         │                   │
         │                   ▼
         │         ┌──────────────────┐
         │         │ Continue Loop    │
         │         └──────────────────┘
         │                   │
         │                   └──────────► (Back to Select Random Face)
         │
         ▼
┌──────────────────────┐
│  End Animation       │
└──────────────────────┘
```

## Rotation Mathematics

For rotating a cubelet around an arbitrary axis through a point:

```
Given:
  - Shape position: S
  - Rotation axis: A (unit vector)
  - Rotation center: C
  - Rotation angle: θ

Steps:
  1. S' = S - C           (translate to origin)
  2. S'' = R(A, θ) × S'   (apply rotation)
  3. S_new = S'' + C      (translate back)

Where R(A, θ) is the rotation matrix constructed from:
  - Axis: A = (ax, ay, az)
  - Angle: θ
```

## File Relationships

```
magic_cube_with_legs.py
  │
  ├─► create_spider()
  ├─► create_cubelet()
  ├─► create_telescoping_leg()
  ├─► create_magic_cube()           ──► Returns cube_objects dict
  ├─► get_face_cubelets(face)       ──┐
  └─► get_face_axis(face)           ──┤
                                      │
                                      │ Used by
                                      │
                                      ▼
animate_magic_cube.py
  │
  ├─► rotate_shape_around_axis()
  ├─► animate_face_rotation()       ──► Uses helpers above
  ├─► perform_random_rotations()    ──► Main animation loop
  ├─► continuous_rotation()         ──► Infinite loop mode
  └─► rebuild_cube_objects()        ──► Load existing cube

run_animation_guide.py
  │
  ├─► validate_scripts()            ──► Check all functions exist
  ├─► print_usage_instructions()    ──► Show how to use
  └─► show_animation_algorithm()    ──► Explain the math
```

## Color Scheme

```
┌─────────────┬──────────┬────────────┐
│ Component   │ Color    │ RGB        │
├─────────────┼──────────┼────────────┤
│ Spider      │ Gray     │ (0.7, 0.7, 0.7) │
│ Centers     │ Red      │ (0.9, 0.5, 0.5) │
│ Edges       │ Green    │ (0.5, 0.9, 0.5) │
│ Corners     │ Blue     │ (0.5, 0.5, 0.9) │
│ Outer Legs  │ Orange   │ (0.8, 0.6, 0.2) │
│ Inner Legs  │ Yellow   │ (0.9, 0.7, 0.3) │
└─────────────┴──────────┴────────────┘
```

## Dimensions (in mm)

```
┌──────────────────────┬───────────┐
│ Component            │ Size      │
├──────────────────────┼───────────┤
│ Spider rod diameter  │ 8 mm      │
│ Spider rod length    │ 82 mm     │
│ Cubelet size         │ 25 mm     │
│ Leg inner diameter   │ 10 mm     │
│ Leg outer diameter   │ 18 mm     │
│ Leg length           │ 75 mm     │
│ Leg offset           │ 20 mm     │
└──────────────────────┴───────────┘
```
