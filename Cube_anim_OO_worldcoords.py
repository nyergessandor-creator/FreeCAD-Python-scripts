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


def run_random_animation(cube, num_moves=10):
    """
    Run random face rotations with random leg extensions.
    
    Args:
        cube: RubiksCube instance
        num_moves: Number of random moves to perform
    """
    face_names = list(cube.faces.keys())
    
    print(f"\nStarting random animation ({num_moves} moves)...")
    
    for move_num in range(num_moves):
        # Random face and direction
        face = random.choice(face_names)
        clockwise = random.choice([True, False])
        
        # Random leg extensions (1-3 legs)
        num_legs = random.randint(1, 3)
        leg_extensions = []
        
        corner_positions = list(cube.corner_cubelets.keys())
        for _ in range(num_legs):
            corner_pos = random.choice(corner_positions)
            target_extension = random.uniform(0.0, 30.0)
            leg_extensions.append((corner_pos, target_extension))
        
        print(f"Move {move_num + 1}: Rotating {face} {'CW' if clockwise else 'CCW'}, extending {num_legs} legs")
        
        # Use the cube's built-in method - all state management is internal
        cube.rotate_face_with_leg_extensions(face, clockwise, leg_extensions)
        
        # Small pause between moves
        time.sleep(0.3)
    
    print("Animation complete!")


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
    print("Watch the cube perform random face rotations with leg extensions!")
    print("(The script will run indefinitely - close the document to stop)")
    
    try:
        move_count = 0
        while True:
            move_count += 1
            print(f"\n=== Move {move_count} ===")
            run_random_animation(cube, num_moves=1)
    except KeyboardInterrupt:
        print("\nAnimation stopped by user.")
    except Exception as e:
        print(f"\nAnimation stopped due to error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_infinite_animation_loop()
