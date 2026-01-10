"""
Animation script for single OOP Rubik's Cube - Version 2
Performs random face rotations with simultaneous leg extensions
All logic is now encapsulated in the RubiksCube class
"""
import FreeCAD as App
import time
import random

# Import the cube classes
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Force reload to get latest version
import importlib
if 'Single_Cube_OOP' in sys.modules:
    importlib.reload(sys.modules['Single_Cube_OOP'])

from Single_Cube_OOP import RubiksCube, CornerCubelet


def run_legs_only_cycle(cube, num_cycles=3):
    """
    Cycle with only leg extensions and retractions.
    
    Args:
        cube: RubiksCube instance
        num_cycles: Number of extend/retract cycles
    """
    print(f"\n=== LEGS ONLY CYCLE ({num_cycles} extend/retract sequences) ===")
    corner_positions = list(cube.corner_cubelets.keys())
    
    for cycle in range(num_cycles):
        # Extend random legs to random lengths
        num_legs = random.randint(3, 6)
        selected_corners = random.sample(corner_positions, num_legs)
        
        print(f"  Cycle {cycle + 1}: Extending {num_legs} legs")
        for corner_pos in selected_corners:
            target = random.uniform(20.0, 40.0)
            cube.animate_leg_extension(corner_pos, target, steps=15, frame_delay=0.02)
        
        time.sleep(0.2)
        
        # Retract all legs back to 0
        print(f"  Cycle {cycle + 1}: Retracting all legs")
        for corner_pos in corner_positions:
            cube.animate_leg_extension(corner_pos, 0.0, steps=15, frame_delay=0.02)
        
        time.sleep(0.2)


def run_rotations_only_cycle(cube, num_rotations=5):
    """
    Cycle with only face rotations, no leg extensions.
    
    Args:
        cube: RubiksCube instance
        num_rotations: Number of random face rotations
    """
    print(f"\n=== ROTATIONS ONLY CYCLE ({num_rotations} face turns) ===")
    face_names = list(cube.faces.keys())
    
    for move in range(num_rotations):
        face = random.choice(face_names)
        clockwise = random.choice([True, False])
        
        print(f"  Rotation {move + 1}: {face} {'CW' if clockwise else 'CCW'}")
        cube.rotate_face(face, clockwise, steps=20, frame_delay=0.02)
        
        time.sleep(0.1)


def run_combined_cycle(cube, num_moves=5):
    """
    Cycle with both face rotations AND leg extensions simultaneously.
    
    Args:
        cube: RubiksCube instance
        num_moves: Number of combined moves
    """
    print(f"\n=== COMBINED CYCLE ({num_moves} rotations with leg extensions) ===")
    face_names = list(cube.faces.keys())
    corner_positions = list(cube.corner_cubelets.keys())
    
    for move in range(num_moves):
        face = random.choice(face_names)
        clockwise = random.choice([True, False])
        
        # Random leg extensions (2-4 legs)
        num_legs = random.randint(2, 4)
        leg_extensions = []
        for _ in range(num_legs):
            corner_pos = random.choice(corner_positions)
            target_extension = random.uniform(10.0, 40.0)
            leg_extensions.append((corner_pos, target_extension))
        
        print(f"  Move {move + 1}: {face} {'CW' if clockwise else 'CCW'} + {num_legs} leg extensions")
        cube.rotate_face_with_leg_extensions(face, clockwise, leg_extensions, steps=20, frame_delay=0.02)
        
        time.sleep(0.1)


def run_infinite_animation_loop():
    """Run infinite animation loop."""
    doc_name = "SingleCube_OOP"
    
    if not App.ActiveDocument or App.ActiveDocument.Name != doc_name:
        print("Please run Single_Cube_OOP.py first to create the cube!")
        return
    
    doc = App.ActiveDocument
    
    # Find the cube object
    cube_obj = doc.getObject("TestCube")
    if not cube_obj:
        print("TestCube not found! Run Single_Cube_OOP.py first.")
        return
    
    # Reconstruct the RubiksCube Python object from FreeCAD objects
    cube = RubiksCube("TestCube")
    cube.model_obj = cube_obj
    cube.doc = doc
    
    # The __init__ already sets up cube.faces, so it should be available
    
    # Rebuild the dictionaries by scanning the model
    for obj in cube_obj.Group:
        if hasattr(obj, 'GridX'):
            grid_pos = (obj.GridX, obj.GridY, obj.GridZ)
            x, y, z = grid_pos
            
            # Determine type based on grid position
            if x != 0 and y != 0 and z != 0:
                # This is a corner
                corner = CornerCubelet(grid_pos, "TestCube")
                corner.part_obj = obj
                
                # Find the inner rod
                for child in obj.Group:
                    if "InnerRod" in child.Name:
                        corner.leg.inner_rod_obj = child
                        break
                
                cube.corner_cubelets[grid_pos] = corner
            elif sum([1 for c in [x, y, z] if c == 0]) == 1:
                # Exactly one coordinate is zero -> edge
                cube.edge_cubelets[grid_pos] = obj
            else:
                # Two coordinates are zero -> center
                cube.center_cubelets[grid_pos] = obj
    
    print(f"Reconstructed cube: {len(cube.corner_cubelets)} corners, {len(cube.edge_cubelets)} edges, {len(cube.center_cubelets)} centers")
    print("\nStarting infinite animation loop...")
    print("Animation sequence: Legs Only → Rotations Only → Combined → Repeat")
    print("(The script will run indefinitely - close the document to stop)")
    
    try:
        sequence_count = 0
        while True:
            sequence_count += 1
            print(f"\n{'='*60}")
            print(f"SEQUENCE {sequence_count}")
            print(f"{'='*60}")
            
            # Cycle 1: Legs only
            run_legs_only_cycle(cube, num_cycles=3)
            time.sleep(0.5)
            
            # Cycle 2: Rotations only
            run_rotations_only_cycle(cube, num_rotations=5)
            time.sleep(0.5)
            
            # Cycle 3: Combined
            run_combined_cycle(cube, num_moves=5)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nAnimation stopped by user.")
    except Exception as e:
        print(f"\nAnimation stopped due to error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_infinite_animation_loop()
