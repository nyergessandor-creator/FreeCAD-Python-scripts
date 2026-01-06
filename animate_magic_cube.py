"""
FreeCAD Animation Script: Magic Cube Face Rotations

This script animates the magic cube by rotating its faces in random order,
similar to the three.js rotating cube demo. Each face rotates 90 degrees
around its axis.

Usage:
    1. First run magic_cube_with_legs.py to create the cube
    2. Then run this script to animate it

Author: Sandor Nyerges
Date: January 6, 2026
"""

import FreeCAD as App
import Part
import math
import random
import time
import sys
import os

# Add the macro directory to Python path for imports
macro_path = os.path.dirname(os.path.abspath(__file__))
if macro_path not in sys.path:
    sys.path.insert(0, macro_path)

# Import the face helper functions from the main script
# We only need CUBELET_SIZE constant now - cubelet gathering is position-based
try:
    from magic_cube_with_legs import CUBELET_SIZE
except ImportError as e:
    print("Error: Could not import from magic_cube_with_legs.py")
    print(f"Import error: {e}")
    print(f"Macro path: {macro_path}")
    print("Make sure the main script is in the same directory.")
    raise


def get_shape_center(shape):
    """
    Get the center of a shape, handling both solids and compounds.
    
    Args:
        shape: Part.Shape object
    
    Returns:
        App.Vector with the center position
    """
    # Try CenterOfMass first (works for solids)
    try:
        return shape.CenterOfMass
    except AttributeError:
        # Fall back to BoundBox center for compounds
        return shape.BoundBox.Center


def get_cubelet_center(cubelet, cube_objects):
    """
    Get the center position of a cubelet, using position tracking for corners.
    
    For corners with fused legs, we use tracked positions that are updated
    during rotations. For centers and edges, we use the actual shape center.
    
    Args:
        cubelet: The cubelet object
        cube_objects: Dictionary with cube object references
    
    Returns:
        App.Vector with the cubelet's current center position
    """
    # Check if this is a corner (has fused legs)
    is_corner = any(cubelet == obj for obj in cube_objects['corners'].values())
    
    if is_corner:
        # Use tracked position from cube_objects
        if 'corner_positions' in cube_objects and cubelet in cube_objects['corner_positions']:
            pos = cube_objects['corner_positions'][cubelet]
            print(f"DEBUG: Corner {cubelet.Label} tracked position: {pos}")
            return pos
        else:
            # Fallback: try to parse from Label2
            if hasattr(cubelet, 'Label2') and cubelet.Label2:
                coords = cubelet.Label2.split(',')
                pos = App.Vector(float(coords[0]), float(coords[1]), float(coords[2]))
                print(f"DEBUG: Corner {cubelet.Label} from Label2: {pos}")
                return pos
            else:
                # Last resort: use shape center (will be inaccurate)
                pos = get_shape_center(cubelet.Shape)
                print(f"DEBUG: Corner {cubelet.Label} using shape center (fallback): {pos}")
                return pos
    else:
        # For centers and edges, just use the shape center directly
        return get_shape_center(cubelet.Shape)


def get_cubelets_at_position(cube_objects, axis_index, slice_value, tolerance=5.0):
    """
    Get all cubelets currently at a specific position along an axis.
    Uses CURRENT position (not stored original) after rotations have occurred.
    
    Args:
        cube_objects: Dictionary with cube object references
        axis_index: 0=X, 1=Y, 2=Z
        slice_value: Position value on that axis (e.g., 25, 0, -25 for spacing)
        tolerance: Position tolerance in mm (increased for safety)
    
    Returns:
        List of cubelet objects currently at that position
    """
    cubelets_at_pos = []
    epsilon = tolerance
    axis_names = ['X', 'Y', 'Z']
    
    # Get all cubelet objects (centers, edges, corners)
    all_cubelets = []
    all_cubelets.extend(cube_objects['centers'].values())
    all_cubelets.extend(cube_objects['edges'].values())
    all_cubelets.extend(cube_objects['corners'].values())
    
    print(f"\nDEBUG: Looking for cubelets at {axis_names[axis_index]}={slice_value} (tolerance={epsilon})")
    
    # Check each cubelet's CURRENT position (not stored original!)
    for cubelet in all_cubelets:
        # Get cubelet center, accounting for fused legs on corners
        center = get_cubelet_center(cubelet, cube_objects)
        
        # Get the coordinate on the specified axis
        if axis_index == 0:
            val = center.x
        elif axis_index == 1:
            val = center.y
        else:
            val = center.z
        
        # Check if this cubelet is at the slice position
        diff = abs(val - slice_value)
        is_match = diff < epsilon
        
        print(f"  {cubelet.Label}: {axis_names[axis_index]}={val:.2f}, diff={diff:.2f}, match={is_match}")
        
        if is_match:
            cubelets_at_pos.append(cubelet)
    
    print(f"DEBUG: Found {len(cubelets_at_pos)} cubelets at position")
    return cubelets_at_pos


def get_legs_for_cubelets(cube_objects, cubelets):
    """
    Get inner leg segments that belong to the given corner cubelets.
    Outer legs are fused into corners, so only inner legs need separate rotation.
    
    Args:
        cube_objects: Dictionary with cube object references
        cubelets: List of cubelet objects
    
    Returns:
        List of (inner_leg, direction) tuples
    """
    legs = []
    
    for cubelet in cubelets:
        # Find inner legs associated with this corner cubelet
        for leg_info in cube_objects['legs']:
            if leg_info['corner_obj'] == cubelet:
                legs.append((leg_info['inner'], leg_info['direction']))
    
    return legs


def animate_leg_telescoping(cube_objects, phase):
    """
    Animate telescoping legs extending and retracting.
    Travel is half the leg length out and back in.
    
    Args:
        cube_objects: Dictionary with cube object references
        phase: Current phase of oscillation (0 to 2*pi)
    
    Returns:
        Updated phase value
    """
    from magic_cube_with_legs import LEG_INNER_LENGTH, LEG_OFFSET
    
    # Calculate extension amount (0 to 0.5 * leg_length)
    max_extension = LEG_INNER_LENGTH / 2
    extension = max_extension * (1 + math.sin(phase)) / 2  # Oscillates 0 to max_extension
    
    # Move inner legs relative to their corners
    for leg_info in cube_objects['legs']:
        direction = leg_info['direction']
        inner_leg = leg_info['inner']
        corner_obj = leg_info['corner_obj']
        
        # Get corner position
        corner_pos = get_shape_center(corner_obj.Shape)
        
        # Recalculate inner leg position based on corner position
        # Outer leg starts at corner + LEG_OFFSET in direction
        # Inner leg extends from outer leg by extension amount
        from magic_cube_with_legs import LEG_INNER_DIAMETER, LEG_INNER_LENGTH, LEG_OUTER_LENGTH
        import Part
        
        outer_start = corner_pos + direction.multiply(LEG_OFFSET)
        inner_start = outer_start + direction.multiply(LEG_OUTER_LENGTH + extension)
        
        new_inner = Part.makeCylinder(
            LEG_INNER_DIAMETER / 2,
            LEG_INNER_LENGTH,
            inner_start,
            direction
        )
        inner_leg.Shape = new_inner
    
    # Increment phase
    phase += 0.05
    if phase > 2 * math.pi:
        phase = 0
    
    return phase


def rotate_shape_around_axis(shape, axis, center, angle_degrees):
    """
    Rotate a shape around an arbitrary axis.
    Returns a new rotated shape to properly trigger FreeCAD updates.
    
    Args:
        shape: Part.Shape to rotate
        axis: App.Vector defining the rotation axis
        center: App.Vector defining the rotation center point
        angle_degrees: Rotation angle in degrees
    
    Returns:
        New rotated Part.Shape
    """
    # Create a copy to avoid modifying the original
    rotated = shape.copy()
    # Translate to origin, rotate, translate back
    rotated.translate(-center)
    rotated.rotate(App.Vector(0, 0, 0), axis, angle_degrees)
    rotated.translate(center)
    
    return rotated


def animate_face_rotation(face, cube_objects, angle=90, steps=20, delay=0.05):
    """
    Animate a face rotation.
    Gathers cubelets by their CURRENT POSITION, not by name.
    This matches real Rubik's cube behavior.
    
    Args:
        face: Face to rotate ('R', 'L', 'U', 'D', 'F', 'B')
        cube_objects: Dictionary with cube object references
        angle: Total rotation angle in degrees (default 90)
        steps: Number of animation steps (default 20)
        delay: Delay between steps in seconds (default 0.05)
    """
    doc = App.ActiveDocument
    if doc is None:
        print("Error: No active document")
        return
    
    # Map face to axis and slice position
    # R/L rotate around X-axis, U/D around Y-axis, F/B around Z-axis
    # Slice at +spacing or -spacing (outer layers only, like three.js)
    face_config = {
        'R': (0, CUBELET_SIZE, App.Vector(1, 0, 0)),   # X-axis, +X slice
        'L': (0, -CUBELET_SIZE, App.Vector(1, 0, 0)),  # X-axis, -X slice
        'U': (1, CUBELET_SIZE, App.Vector(0, 1, 0)),   # Y-axis, +Y slice
        'D': (1, -CUBELET_SIZE, App.Vector(0, 1, 0)),  # Y-axis, -Y slice
        'F': (2, CUBELET_SIZE, App.Vector(0, 0, 1)),   # Z-axis, +Z slice
        'B': (2, -CUBELET_SIZE, App.Vector(0, 0, 1)),  # Z-axis, -Z slice
    }
    
    if face not in face_config:
        print(f"Error: Invalid face {face}")
        return
    
    axis_index, slice_value, axis_vector = face_config[face]
    
    # Get cubelets at this position RIGHT NOW (not by name!)
    cubelets = get_cubelets_at_position(cube_objects, axis_index, slice_value)
    if not cubelets:
        print(f"Warning: No cubelets found at position for face {face}")
        return
    
    # Get legs associated with these cubelets
    legs_to_rotate = get_legs_for_cubelets(cube_objects, cubelets)
    
    # Rotation center is on the axis at the slice position
    center = App.Vector(0, 0, 0)
    if axis_index == 0:
        center.x = slice_value
    elif axis_index == 1:
        center.y = slice_value
    else:
        center.z = slice_value
    
    # Calculate angle per step
    angle_per_step = angle / steps
    
    # Debug output
    cubelet_names = [c.Name for c in cubelets]
    axis_names = ['X', 'Y', 'Z']
    print(f"\nRotating {face} face: {len(cubelets)} cubelets, {len(legs_to_rotate)} inner legs")
    
    # Animate rotation
    for step in range(steps):
        # Rotate cubelets (outer legs are fused in, so they rotate automatically)
        for cubelet in cubelets:
            # Rotate and REASSIGN the shape to trigger FreeCAD update
            cubelet.Shape = rotate_shape_around_axis(
                cubelet.Shape,
                axis_vector,
                center,
                angle_per_step
            )
            
            # Update tracked position for corners
            if cubelet in cube_objects.get('corner_positions', {}):
                old_pos = cube_objects['corner_positions'][cubelet]
                # Rotate the position vector around the axis
                new_pos = App.Vector(old_pos.x, old_pos.y, old_pos.z)
                new_pos = new_pos - center  # Translate to rotation center
                # Rotate using rotation matrix would be complex, so use FreeCAD's rotation
                import Part
                temp_vertex = Part.Vertex(new_pos)
                temp_vertex.rotate(App.Vector(0,0,0), axis_vector, angle_per_step)
                new_pos = temp_vertex.Point
                new_pos = new_pos + center  # Translate back
                cube_objects['corner_positions'][cubelet] = new_pos
        
        # Rotate inner legs with their corners
        for inner_leg, direction in legs_to_rotate:
            inner_leg.Shape = rotate_shape_around_axis(
                inner_leg.Shape,
                axis_vector,
                center,
                angle_per_step
            )
        
        # Update display
        doc.recompute()
        App.Gui.updateGui()
        
        # Process Qt events to ensure GUI updates are rendered
        try:
            from PySide import QtCore
            QtCore.QCoreApplication.processEvents()
        except:
            try:
                from PySide2 import QtCore
                QtCore.QCoreApplication.processEvents()
            except:
                pass
        
        # Small delay for animation
        time.sleep(delay)
    
    # Rotation complete (silent)


def perform_random_rotations(cube_objects, num_moves=10, steps_per_move=15):
    """
    Perform random face rotations on the cube.
    
    Args:
        cube_objects: Dictionary with cube object references
        num_moves: Number of random moves to perform
        steps_per_move: Animation steps for each move
    """
    faces = ['R', 'L', 'U', 'D', 'F', 'B']
    directions = [90, -90]  # Clockwise or counter-clockwise
    
    print("\n" + "="*60)
    print("Starting Random Cube Animation")
    print("="*60)
    print(f"Performing {num_moves} random moves...")
    print("Press Ctrl+C to stop\n")
    
    try:
        for move_num in range(num_moves):
            # Choose random face and direction
            face = random.choice(faces)
            angle = random.choice(directions)
            
            direction_str = "CW" if angle > 0 else "CCW"
            print(f"Move {move_num + 1}/{num_moves}: {face} {direction_str}")
            
            # Animate the rotation
            animate_face_rotation(face, cube_objects, angle, steps_per_move, delay=0.03)
            
            # Brief pause between moves
            time.sleep(0.2)
        
        print("\n" + "="*60)
        print("Animation Complete!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\nAnimation stopped by user")


def continuous_rotation(cube_objects):
    """
    Continuously perform random rotations (infinite loop).
    Press Ctrl+C to stop.
    
    Args:
        cube_objects: Dictionary with cube object references
    """
    print("\n" + "="*60)
    print("Starting Continuous Cube Animation")
    print("="*60)
    print("Press Ctrl+C to stop\n")
    
    faces = ['R', 'L', 'U', 'D', 'F', 'B']
    directions = [90, -90]
    
    move_count = 0
    telescoping_phase = 0.0  # For leg extension/retraction animation
    
    try:
        while True:
            face = random.choice(faces)
            angle = random.choice(directions)
            
            direction_str = "CW" if angle > 0 else "CCW"
            move_count += 1
            print(f"Move {move_count}: {face} {direction_str}")
            
            animate_face_rotation(face, cube_objects, angle, steps=15, delay=0.03)
            
            # Skip telescoping for now - it causes geometry corruption after rotations
            # TODO: Fix direction vector tracking after rotations
            # telescoping_phase = animate_leg_telescoping(cube_objects, telescoping_phase)
            
            time.sleep(0.2)
            
    except KeyboardInterrupt:
        print(f"\nAnimation stopped after {move_count} moves")


def rebuild_cube_objects():
    """
    Rebuild the cube_objects dictionary from the active document.
    Call this if you ran the creation script separately.
    
    Returns:
        Dictionary with cube object references
    """
    doc = App.ActiveDocument
    if doc is None:
        print("Error: No active document")
        return None
    
    cube_objects = {
        'spider': None,
        'centers': {},
        'edges': {},
        'corners': {},
        'legs': [],
        'corner_positions': {}  # Track corner positions through rotations
    }
    
    # Find objects by name and rebuild leg associations
    inner_legs = {}
    
    for obj in doc.Objects:
        name = obj.Name
        
        if name == "Spider":
            cube_objects['spider'] = obj
        elif name.startswith("Center_"):
            face = name.split("_")[1]
            cube_objects['centers'][face] = obj
        elif name.startswith("Edge_"):
            edge = name.split("_")[1]
            cube_objects['edges'][edge] = obj
        elif name.startswith("Corner_"):
            corner = name.split("_")[1]
            cube_objects['corners'][corner] = obj
        elif name.startswith("InnerLeg_"):
            corner = name.split("_")[1]
            inner_legs[corner] = obj
        # Note: OuterLeg objects don't exist - they're fused into corners
    
    # Rebuild leg associations with corners (only inner legs)
    for corner_name, inner_obj in inner_legs.items():
        if corner_name in cube_objects['corners']:
            corner_obj = cube_objects['corners'][corner_name]
            
            # Try to get direction from stored Label2, or calculate from current position
            try:
                if hasattr(corner_obj, 'Label2') and corner_obj.Label2:
                    # Parse stored position
                    coords = corner_obj.Label2.split(',')
                    corner_pos = App.Vector(float(coords[0]), float(coords[1]), float(coords[2]))
                else:
                    # Calculate from current position
                    corner_pos = get_shape_center(corner_obj.Shape)
            except:
                # Fall back to current position
                corner_pos = get_shape_center(corner_obj.Shape)
            
            # IMPORTANT: normalize() modifies the vector in place, so make a copy first!
            direction = App.Vector(corner_pos.x, corner_pos.y, corner_pos.z)
            direction.normalize()
            
            # Initialize tracked position for this corner (use original corner_pos, not normalized!)
            cube_objects['corner_positions'][corner_obj] = corner_pos
            
            cube_objects['legs'].append({
                'corner': corner_name,
                'corner_obj': corner_obj,
                'inner': inner_obj,
                'direction': direction
            })
    
    print(f"Found {len(cube_objects['centers'])} centers, " +
          f"{len(cube_objects['edges'])} edges, " +
          f"{len(cube_objects['corners'])} corners (with fused outer legs), " +
          f"{len(cube_objects['legs'])} inner legs")
    
    return cube_objects


def test_single_rotation(face='R'):
    """
    Test a single face rotation with detailed output.
    
    Args:
        face: Face to test ('R', 'L', 'U', 'D', 'F', 'B')
    """
    cube_objects = rebuild_cube_objects()
    if cube_objects:
        print(f"\n{'='*60}")
        print(f"Testing {face} face rotation...")
        print(f"{'='*60}")
        
        # Show what we found
        print(f"\nCube structure loaded:")
        print(f"  Centers: {len(cube_objects['centers'])} - {list(cube_objects['centers'].keys())}")
        print(f"  Edges: {len(cube_objects['edges'])} - {list(cube_objects['edges'].keys())}")
        print(f"  Corners: {len(cube_objects['corners'])} - {list(cube_objects['corners'].keys())}")
        print(f"  Leg sets: {len(cube_objects['legs'])} - corners: {[l['corner'] for l in cube_objects['legs']]}")
        
        print(f"\nStarting SLOW rotation for debugging...")
        print("Watch the 3D view carefully!\n")
        animate_face_rotation(face, cube_objects, angle=90, steps=30, delay=0.1)
        print(f"\n{'='*60}")
        print("Test complete!")
        print(f"{'='*60}")


# Main execution
if __name__ == "__main__":
    try:
        # Check if FreeCAD GUI is available
        if not hasattr(App, 'Gui'):
            print("Error: This script requires FreeCAD GUI")
            print("Please run this script from within FreeCAD")
            exit(1)
        
        # Rebuild cube objects from active document
        print("Loading cube from active document...")
        cube_objects = rebuild_cube_objects()
        
        if cube_objects is None:
            print("\nError: Could not load cube objects")
            print("Make sure you have run magic_cube_with_legs.py first")
            exit(1)
        
        # Show menu
        print("\n" + "="*60)
        print("Magic Cube Animation Menu")
        print("="*60)
        print("1. Perform 10 random rotations")
        print("2. Perform 20 random rotations")
        print("3. Continuous rotation (infinite loop) - DEFAULT")
        print("4. Test single face rotation (R face)")
        print("="*60)
        
        # For automated execution, do continuous mode
        choice = 3  # Continuous mode
        
        if choice == 1:
            perform_random_rotations(cube_objects, num_moves=10, steps_per_move=15)
        elif choice == 2:
            perform_random_rotations(cube_objects, num_moves=20, steps_per_move=15)
        elif choice == 3:
            continuous_rotation(cube_objects)
        elif choice == 4:
            test_single_rotation('R')
        
        print("\nAnimation script finished!")
        print("You can run this script again to perform more animations")
        
    except Exception as e:
        print(f"\nError during animation: {str(e)}")
        import traceback
        traceback.print_exc()
