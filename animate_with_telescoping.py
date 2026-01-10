"""
FreeCAD Script: Animate Rubik's Cube with Face Rotations and Telescoping Legs
-----------------------------------------------------------------------------
This script animates:
- Random 90-degree face rotations using pivot grouping
- Simultaneous telescoping of corner legs (30mm extension/retraction)

Usage:
    1. Run assembly_magic_cube_with_constraints.py first
    2. Run this script to animate

Author: GitHub Copilot
"""

import FreeCAD as App
import Part
import time
import random
import math

# Animation settings
ROTATION_STEPS = 30  # Smooth 90-degree rotation
STEP_DELAY = 0.03  # 30ms between steps
MOVES_TO_SHOW = 10

# Cube parameters (must match assembly script)
CUBELET_SIZE = 25.0
GAP = 0.0
SPACING = CUBELET_SIZE + GAP

# Leg parameters (must match assembly script)
LEG_OUTER_LENGTH = 30.0
LEG_OUTER_DIAMETER = 15.0
LEG_INNER_LENGTH = 50.0
LEG_INNER_DIAMETER = 10.0
LEG_OVERLAP = 10.0

# Telescoping parameters
TELESCOPE_EXTENSION = 30.0  # How far legs extend/retract (mm)
LEG_SPEED_MIN = 5.0  # Minimum mm per rotation cycle
LEG_SPEED_MAX = 15.0  # Maximum mm per rotation cycle
EPSILON = 1.0


def get_all_cubelets():
    """Returns all cubelet Part objects with their grid positions."""
    doc = App.ActiveDocument
    cubelets = []
    
    # Find the Model container
    model = None
    for obj in doc.Objects:
        if obj.Label == "Model" and obj.TypeId == "App::Part":
            model = obj
            break
    
    if model is None:
        print("Error: Model container not found!")
        return []
    
    # Search within the Model container's Group
    for obj in model.Group:
        if obj.TypeId == "App::Part" and obj.Name != "Pivot":
            if hasattr(obj, 'GridX') and hasattr(obj, 'GridY') and hasattr(obj, 'GridZ'):
                cubelets.append(obj)
    
    return cubelets


def get_corner_cubelets():
    """Returns only corner cubelet Part objects (those with legs)."""
    cubelets = get_all_cubelets()
    corners = []
    
    for cubelet in cubelets:
        # Corner pieces have all three grid coords as ±1
        if (abs(cubelet.GridX) == 1 and 
            abs(cubelet.GridY) == 1 and 
            abs(cubelet.GridZ) == 1):
            corners.append(cubelet)
    
    return corners


def get_face_cubelets_by_grid(face_name):
    """Returns cubelets at a face using grid coordinates."""
    cubelets = get_all_cubelets()
    face_cubelets = []
    
    face_checks = {
        'R': ('GridX', 1),
        'L': ('GridX', -1),
        'U': ('GridY', 1),
        'D': ('GridY', -1),
        'F': ('GridZ', 1),
        'B': ('GridZ', -1),
    }
    
    if face_name not in face_checks:
        return face_cubelets
    
    attr_name, target_value = face_checks[face_name]
    
    for cubelet in cubelets:
        if getattr(cubelet, attr_name) == target_value:
            face_cubelets.append(cubelet)
    
    return face_cubelets


def get_rotation_axis(face_name):
    """Returns the rotation axis vector for a given face."""
    axis_map = {
        'R': App.Vector(1, 0, 0),
        'L': App.Vector(1, 0, 0),
        'U': App.Vector(0, 1, 0),
        'D': App.Vector(0, 1, 0),
        'F': App.Vector(0, 0, 1),
        'B': App.Vector(0, 0, 1),
    }
    return axis_map.get(face_name, App.Vector(0, 0, 1))


def create_pivot():
    """Creates or retrieves a pivot Part for temporary cubelet grouping."""
    doc = App.ActiveDocument
    
    for obj in doc.Objects:
        if obj.Name == "Pivot" and obj.TypeId == "App::Part":
            return obj
    
    pivot = doc.addObject("App::Part", "Pivot")
    model = doc.getObject("Model")
    if model:
        model.addObject(pivot)
    
    return pivot


def move_to_pivot(cubelet, pivot):
    """Moves a cubelet from the Model to the Pivot, preserving world position."""
    doc = App.ActiveDocument
    model = doc.getObject("Model")
    
    if not model or cubelet.Name == "Spider":
        return False
    
    world_placement = cubelet.getGlobalPlacement()
    
    if hasattr(model, 'removeObject'):
        model.removeObject(cubelet)
    
    pivot.addObject(cubelet)
    
    pivot_world = pivot.getGlobalPlacement()
    local_placement = pivot_world.inverse().multiply(world_placement)
    cubelet.Placement = local_placement
    
    return True


def move_to_model(cubelet):
    """Moves a cubelet from the Pivot back to the Model, preserving world position."""
    doc = App.ActiveDocument
    model = doc.getObject("Model")
    pivot = doc.getObject("Pivot")
    
    if not model or not pivot:
        return False
    
    world_placement = cubelet.getGlobalPlacement()
    
    if hasattr(pivot, 'removeObject'):
        pivot.removeObject(cubelet)
    
    model.addObject(cubelet)
    
    model_world = model.getGlobalPlacement()
    local_placement = model_world.inverse().multiply(world_placement)
    cubelet.Placement = local_placement
    
    return True


def snap_position(value, grid_spacing):
    """Snaps a value to the nearest grid point."""
    return round(value / grid_spacing) * grid_spacing


def update_grid_positions():
    """Updates GridX/Y/Z properties based on current world positions."""
    cubelets = get_all_cubelets()
    
    for cubelet in cubelets:
        # Get world position to calculate grid coordinates
        world_pos = cubelet.getGlobalPlacement().Base
        
        cubelet.GridX = round(world_pos.x / SPACING)
        cubelet.GridY = round(world_pos.y / SPACING)
        cubelet.GridZ = round(world_pos.z / SPACING)


def animate_face_rotation_with_telescoping(face_name, clockwise=True):
    """
    Rotates a face 90 degrees with simultaneous leg telescoping.
    Legs extend if retracted, retract if extended.
    
    Args:
        face_name: 'R', 'L', 'U', 'D', 'F', 'B'
        clockwise: rotation direction
    """
    doc = App.ActiveDocument
    
    # Gather cubelets at this face
    cubelets = get_face_cubelets_by_grid(face_name)
    
    if not cubelets:
        print(f"No cubelets found for face {face_name}")
        return
    
    direction = "CW" if clockwise else "CCW"
    print(f"Rotating {face_name} face {direction} - {len(cubelets)} cubelets")
    
    # Create/get pivot (reuse existing pivot to preserve rotation state)
    pivot = create_pivot()
    doc.recompute()
    
    # Attach cubelets to pivot
    attached_cubelets = []
    for cubelet in cubelets:
        if move_to_pivot(cubelet, pivot):
            attached_cubelets.append(cubelet)
    
    doc.recompute()
    
    if not attached_cubelets:
        print(f"No cubelets could be attached to pivot")
        return
    
    # Rotation parameters
    axis = get_rotation_axis(face_name)
    center = App.Vector(0, 0, 0)
    total_angle = 90 if clockwise else -90
    angle_per_step = total_angle / ROTATION_STEPS
    
    # Determine which corners need to telescope and how much they move this cycle
    corners_to_animate = {}
    for cubelet in attached_cubelets:
        if hasattr(cubelet, 'LegExtension') and hasattr(cubelet, 'LegTargetExtension') and hasattr(cubelet, 'LegSpeed'):
            current = cubelet.LegExtension
            target = cubelet.LegTargetExtension
            speed = cubelet.LegSpeed
            
            # Check if leg has reached its target or needs a new target
            if abs(current - target) < 2.0:  # Within 2mm of target
                # Pick a new random target (either 0 or 30mm)
                if abs(current) < 15:  # Currently retracted or mid-way retracting
                    new_target = TELESCOPE_EXTENSION  # Extend
                else:  # Currently extended or mid-way extending
                    new_target = 0.0  # Retract
                
                # Assign random speed for this movement
                import random
                cubelet.LegTargetExtension = new_target
                cubelet.LegSpeed = random.uniform(LEG_SPEED_MIN, LEG_SPEED_MAX)
                target = new_target
                speed = cubelet.LegSpeed
            
            # Calculate movement for this cycle
            remaining = target - current
            movement_this_cycle = max(min(speed, abs(remaining)), 0) * (1 if remaining > 0 else -1)
            
            if abs(movement_this_cycle) > 0.1:  # Only animate if significant movement
                corners_to_animate[cubelet] = movement_this_cycle
    
    if corners_to_animate:
        actions = []
        for cubelet, movement in corners_to_animate.items():
            direction = "extending" if movement > 0 else "retracting"
            actions.append(f"{cubelet.Label}: {direction} {abs(movement):.1f}mm")
        print(f"  Legs: {', '.join(actions)}")
    
    # Animate rotation AND telescoping simultaneously
    for step in range(ROTATION_STEPS):
        # Rotate pivot
        pivot.Placement.rotate(center, axis, angle_per_step)
        
        # Telescope corner legs that are in the rotating face
        for cubelet, total_movement in corners_to_animate.items():
            movement_per_step = total_movement / ROTATION_STEPS
            
            # Find the inner rod child object
            for obj in cubelet.Group:
                if obj.Name.startswith("InnerRod_"):
                    # Move inner rod along leg diagonal (using * to avoid mutation)
                    diagonal = cubelet.LegDiagonal
                    translation = diagonal * movement_per_step
                    obj.Placement.Base = obj.Placement.Base + translation
                    
                    # Track extension (only update on last step to avoid rounding errors)
                    if step == ROTATION_STEPS - 1:
                        cubelet.LegExtension += total_movement
                    break
        
        doc.recompute()
        App.Gui.updateGui()
        time.sleep(STEP_DELAY)
    
    # Final recompute to ensure exact final position
    doc.recompute()
    
    # Detach cubelets (they maintain their rotated world positions)
    for cubelet in attached_cubelets:
        move_to_model(cubelet)
    
    doc.recompute()
    
    # Reset pivot to identity for next rotation
    pivot.Placement = App.Placement()
    doc.recompute()
    
    # Update grid positions based on new world positions
    update_grid_positions()
    
    print(f"Completed rotation of {face_name} face")


def animate_random_moves():
    """Performs random face rotations with alternating leg extension/retraction."""
    doc = App.ActiveDocument
    
    if not doc:
        print("Error: No active document!")
        print("Run assembly_magic_cube_with_constraints.py to create it.")
        return
    
    print(f"Active document: {doc.Name}")
    
    cubelets = get_all_cubelets()
    
    if not cubelets:
        print("Error: No cubelets with grid properties found!")
        return
    
    print(f"Found {len(cubelets)} cubelets with grid properties")
    
    faces = ['R', 'L', 'U', 'D', 'F', 'B']
    
    print(f"\nStarting infinite animation loop...")
    print("Press Ctrl+C in the Python console to stop")
    print("=" * 60)
    
    move_num = 0
    while True:
        move_num += 1
        face = random.choice(faces)
        clockwise = random.choice([True, False])
        
        print(f"\nMove {move_num}:")
        animate_face_rotation_with_telescoping(face, clockwise)
        
        time.sleep(0.3)


if __name__ == "__main__":
    animate_random_moves()
