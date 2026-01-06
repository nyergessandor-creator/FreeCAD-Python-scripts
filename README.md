# FreeCAD-Python-scripts

Python scripts for FreeCAD to design and animate a magic cube with telescoping legs.

## Magic Cube with Legs and Animation

A self-reconfigurable modular robotics system inspired by three.js rotating cube demos.

### Features

- **Spider Structure**: Three orthogonal rods forming the rigid central frame
- **26 Cubelets**: 
  - 6 center cubelets (red, one per face)
  - 12 edge cubelets (green)
  - 8 corner cubelets (blue)
- **8 Telescoping Legs**: Prismatic joints at each corner
- **Animated Face Rotations**: Random 90-degree face rotations similar to Rubik's cube

### Files

1. **magic_cube_with_legs.py** - Main script to create the cube structure
   - Creates spider, cubelets, and telescoping legs
   - Groups cubelets by face (R, L, U, D, F, B)
   - Provides helper functions for animation

2. **animate_magic_cube.py** - Animation script
   - Performs random face rotations
   - Smooth animations with configurable steps
   - Three modes: 10 moves, 20 moves, or continuous

3. **run_animation_guide.py** - Setup validation and usage guide
   - Validates script structure
   - Provides detailed instructions
   - Shows animation algorithm

### Usage

#### In FreeCAD GUI (Recommended)

1. Open FreeCAD
2. Go to **Macro > Macros...**
3. Click **Execute** on `magic_cube_with_legs.py` to create the cube
4. Click **Execute** on `animate_magic_cube.py` to watch it animate

#### Command Line

```bash
# Create the cube
freecadcmd magic_cube_with_legs.py

# Then open FreeCAD GUI and run animate_magic_cube.py
# (Animation requires GUI for visual updates)
```

### Animation Details

The animation implements:
- **Random face selection** from R, L, U, D, F, B (Rubik's cube notation)
- **Random direction** (clockwise or counter-clockwise 90°)
- **Smooth rotation** with 15-20 animation steps per move
- **Proper face grouping** - each face contains 9 cubelets (1 center, 4 edges, 4 corners)

### Technical Details

- **Rotation Algorithm**: 
  1. Translate cubelets to origin
  2. Apply rotation matrix around axis
  3. Translate back to face center
  
- **Face Axes**:
  - R/L (Right/Left): X-axis
  - U/D (Up/Down): Y-axis
  - F/B (Front/Back): Z-axis

### Requirements

- FreeCAD 0.19 or later
- Python 3.x (included with FreeCAD)

### Installation

#### Windows
Download from https://www.freecad.org/downloads.php

#### Linux
```bash
sudo apt install freecad
```

#### macOS
```bash
brew install freecad
```

### Author

Sandor Nyerges

### Date

January 5-6, 2026

