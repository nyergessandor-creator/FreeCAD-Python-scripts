"""
Animation script for two connected OOP Rubik's Cubes
Creates an anchor cube with a load cube connected via telescoping legs
The load cube moves as the anchor cube performs face rotations and leg extensions

VERSION 3.0 - CUBELET TRACKING FIX
Key fix: Tracks the specific physical cubelet object with the connection leg,
not the grid position (1,1,1). After face rotations, a different cubelet may
occupy position (1,1,1), but we need to track the original corner that has
the red leg attached. This ensures the load cube follows the correct corner.
"""
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui, QtCore
import time
import random
import math

# Import the cube classes
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Force reload to get latest version
import importlib
if 'Cube_OO_grids' in sys.modules:
    importlib.reload(sys.modules['Cube_OO_grids'])

from Cube_OO_grids import RubiksCube, CornerCubelet

# Constants for leg connection
LEG_EXTENSION_TO_MEET = 25.0  # mm each leg extends to meet in middle
CUBELET_SIZE = 25.0
SPACING = 25.0
LEG_INNER_DIAMETER = 10.0

# Global variable to track the specific anchor corner cubelet with connection leg
_anchor_connection_cubelet = None


def calculate_load_cube_position():
    """
    Calculate where the load cube should be positioned to connect to anchor cube's (1,1,1) corner.
    Legs start at home position (0mm extension) - spheres just touching (not overlapping).
    
    Returns:
        App.Vector: Position for the load cube center
    """
    diagonal = App.Vector(1, 1, 1)
    diagonal.normalize()
    
    # Anchor corner cubelet is at (25, 25, 25) in world coords
    corner_point_local = App.Vector(1, 1, 1) * (CUBELET_SIZE / 2)
    SPHERE_RADIUS = LEG_INNER_DIAMETER / 2
    
    # Anchor leg: from corner center to sphere CENTER at home position
    # 58mm base + 0mm extension = 58mm to sphere center
    anchor_sphere_center_offset = corner_point_local + diagonal * (58.0 + 0.0)
    
    # Anchor corner world position
    anchor_corner_world = App.Vector(SPACING, SPACING, SPACING)
    anchor_sphere_center_world = anchor_corner_world + anchor_sphere_center_offset
    
    # The touching point between spheres is one radius away from each sphere center
    # along the connection axis
    touching_point = anchor_sphere_center_world + diagonal * SPHERE_RADIUS
    
    # Load cube's (-1,-1,-1) corner leg - sphere center is one radius before touching point
    load_diagonal = App.Vector(-1, -1, -1)
    load_diagonal.normalize()
    load_sphere_center_world = touching_point + load_diagonal * SPHERE_RADIUS
    
    # Work backwards from load sphere center to load cube center
    load_corner_point_local = App.Vector(-1, -1, -1) * (CUBELET_SIZE / 2)
    # 58mm base + 0mm extension = 58mm from corner to sphere center
    load_sphere_center_offset = load_corner_point_local + load_diagonal * (58.0 + 0.0)
    
    # Load cube center
    load_center = load_sphere_center_world - load_sphere_center_offset
    
    return load_center


def update_load_cube_position(anchor_cube, load_cube, anchor_connection_cubelet):
    """
    Update the load cube's position and orientation based on the anchor cube's corner leg position.
    The load cube should behave as if its blue leg is rigidly attached to the anchor's red leg.
    
    Args:
        anchor_cube: RubiksCube instance (anchor)
        load_cube: RubiksCube instance (load)
        anchor_connection_cubelet: The specific CornerCubelet object with the red connection leg
    """
    # Use the specific cubelet object, not a position lookup
    anchor_corner = anchor_connection_cubelet
    if not anchor_corner:
        print("ERROR: Anchor corner not found")
        return
    
    # Get anchor corner's world placement (includes rotation from face rotations)
    anchor_corner_placement = anchor_corner.part_obj.getGlobalPlacement()
    
    # Get the leg tip position in world coordinates
    anchor_leg_tip_world = anchor_corner.leg.get_tip_position_world()
    
    print(f"  [DEBUG] Red leg tip at: {anchor_leg_tip_world}, extension: {anchor_corner.leg.extension:.1f}mm")
    
    # Get current extension of load corner leg
    load_corner = load_cube.corner_cubelets.get((-1, -1, -1))
    if not load_corner:
        print("ERROR: Load corner not found")
        return
    
    current_extension = load_corner.leg.extension
    SPHERE_RADIUS = LEG_INNER_DIAMETER / 2
    
    # FIX: Compensate for 43.3mm overlap in calculation
    GAP_CORRECTION = 43.3
    
    # Calculate load cube rotation to maintain rigid attachment
    # The anchor corner's diagonal direction after rotation
    local_diagonal = App.Vector(1, 1, 1)
    local_diagonal.normalize()
    rotated_diagonal = anchor_corner_placement.Rotation.multVec(local_diagonal)
    
    # Load cube should be rotated so its (-1,-1,-1) direction opposes the anchor's (1,1,1)
    # Take anchor rotation and flip 180 degrees around the connection axis
    load_rotation = anchor_corner_placement.Rotation
    flip_rotation = App.Rotation(rotated_diagonal, 180)
    load_rotation = flip_rotation.multiply(load_rotation)
    
    # Calculate load position with rotation applied
    load_corner_point_local = App.Vector(-1, -1, -1) * (CUBELET_SIZE / 2)
    load_local_diagonal = App.Vector(-1, -1, -1)
    load_local_diagonal.normalize()
    load_leg_tip_offset_local = load_corner_point_local + load_local_diagonal * (58.0 + current_extension + SPHERE_RADIUS)
    
    # Apply rotation to the offset
    load_leg_tip_offset_rotated = load_rotation.multVec(load_leg_tip_offset_local)
    
    # Calculate new load cube center - add gap correction along the connection axis
    new_load_center = anchor_leg_tip_world - load_leg_tip_offset_rotated + rotated_diagonal * GAP_CORRECTION
    
    print(f"  [DEBUG] Moving load cube to: {new_load_center}, blue leg extension: {current_extension:.1f}mm")
    
    # Apply position and rotation to load cube
    load_cube.model_obj.Placement.Base = new_load_center
    load_cube.model_obj.Placement.Rotation = load_rotation
    load_cube.doc.recompute()


def _rotate_face_with_load_tracking(anchor_cube, load_cube, anchor_connection_cubelet, face_name, clockwise=True, steps=30, frame_delay=0.05):
    """
    Rotate anchor cube face while updating load cube position at each step.
    This is a custom version of rotate_face that calls update_load_cube_position during animation.
    """
    import time
    
    face_info = anchor_cube.faces[face_name]
    axis = App.Vector(*face_info["axis"])
    
    # Get face cubelets
    face_cubelets = anchor_cube._get_face_cubelets(face_name)
    
    if not face_cubelets:
        print(f"Warning: No cubelets found for face {face_name}")
        return
    
    # Create pivot
    pivot = anchor_cube.doc.addObject("App::Part", f"Pivot_{face_name}")
    anchor_cube.model_obj.addObject(pivot)
    
    # Move cubelets to pivot
    for cubelet in face_cubelets:
        anchor_cube.model_obj.removeObject(cubelet)
        pivot.addObject(cubelet)
    
    # Center of rotation
    center = axis * SPACING
    
    # Animate rotation - slower for observation
    angle_per_step = (90.0 / steps) if clockwise else (-90.0 / steps)
    
    for step in range(steps):
        pivot.Placement.Rotation = App.Rotation(axis, angle_per_step * (step + 1))
        pivot.Placement.Base = center - pivot.Placement.Rotation.multVec(center)
        
        anchor_cube.doc.recompute()
        
        # Update load cube position at each step
        update_load_cube_position(anchor_cube, load_cube, anchor_connection_cubelet)
        
        App.Gui.updateGui()
        time.sleep(frame_delay)
    
    # Finalize rotation - snap to exact angle
    final_rotation = App.Rotation(axis, 90.0 if clockwise else -90.0)
    pivot.Placement.Rotation = final_rotation
    pivot.Placement.Base = center - pivot.Placement.Rotation.multVec(center)
    
    # Move cubelets back to model, applying the rotation
    for cubelet in face_cubelets:
        # Get world placement
        world_placement = cubelet.getGlobalPlacement()
        
        # Remove from pivot, add to model
        pivot.removeObject(cubelet)
        anchor_cube.model_obj.addObject(cubelet)
        
        # Set new placement
        cubelet.Placement = world_placement
    
    # Remove pivot
    anchor_cube.model_obj.removeObject(pivot)
    anchor_cube.doc.removeObject(pivot.Name)
    anchor_cube.doc.recompute()
    
    # Final update of load position
    update_load_cube_position(anchor_cube, load_cube, anchor_connection_cubelet)


def _rotate_with_legs_and_load_tracking(anchor_cube, load_cube, anchor_connection_cubelet, face_name, clockwise=True, leg_extensions=None, steps=30, frame_delay=0.05):
    """
    Rotate anchor cube face with leg extensions while updating load cube position at each step.
    """
    import time
    
    if leg_extensions is None:
        leg_extensions = []
    
    face_info = anchor_cube.faces[face_name]
    axis = App.Vector(*face_info["axis"])
    
    # Get face cubelets
    face_cubelets = anchor_cube._get_face_cubelets(face_name)
    
    if not face_cubelets:
        print(f"Warning: No cubelets found for face {face_name}")
        return
    
    # Store initial extensions for legs
    leg_initial_extensions = {}
    leg_target_extensions = {}
    for corner_pos, target_ext in leg_extensions:
        corner = anchor_cube.corner_cubelets.get(corner_pos)
        if corner:
            leg_initial_extensions[corner_pos] = corner.leg.extension
            leg_target_extensions[corner_pos] = target_ext
    
    # Create pivot
    pivot = anchor_cube.doc.addObject("App::Part", f"Pivot_{face_name}")
    anchor_cube.model_obj.addObject(pivot)
    
    # Move cubelets to pivot
    for cubelet in face_cubelets:
        anchor_cube.model_obj.removeObject(cubelet)
        pivot.addObject(cubelet)
    
    # Center of rotation
    center = axis * SPACING
    
    # Animate rotation with leg extensions
    angle_per_step = (90.0 / steps) if clockwise else (-90.0 / steps)
    
    for step in range(steps):
        # Rotate pivot
        pivot.Placement.Rotation = App.Rotation(axis, angle_per_step * (step + 1))
        pivot.Placement.Base = center - pivot.Placement.Rotation.multVec(center)
        
        # Update leg extensions
        progress = (step + 1) / steps
        for corner_pos in leg_target_extensions:
            corner = anchor_cube.corner_cubelets.get(corner_pos)
            if corner:
                initial = leg_initial_extensions[corner_pos]
                target = leg_target_extensions[corner_pos]
                current_ext = initial + (target - initial) * progress
                corner.leg.set_extension(current_ext)
        
        anchor_cube.doc.recompute()
        
        # Update load cube position at each step
        update_load_cube_position(anchor_cube, load_cube, anchor_connection_cubelet)
        
        App.Gui.updateGui()
        time.sleep(frame_delay)
    
    # Finalize rotation
    final_rotation = App.Rotation(axis, 90.0 if clockwise else -90.0)
    pivot.Placement.Rotation = final_rotation
    pivot.Placement.Base = center - pivot.Placement.Rotation.multVec(center)
    
    # Set final leg extensions
    for corner_pos, target_ext in leg_extensions:
        corner = anchor_cube.corner_cubelets.get(corner_pos)
        if corner:
            corner.leg.set_extension(target_ext)
    
    # Move cubelets back to model
    for cubelet in face_cubelets:
        world_placement = cubelet.getGlobalPlacement()
        pivot.removeObject(cubelet)
        anchor_cube.model_obj.addObject(cubelet)
        cubelet.Placement = world_placement
    
    # Remove pivot
    anchor_cube.model_obj.removeObject(pivot)
    anchor_cube.doc.removeObject(pivot.Name)
    anchor_cube.doc.recompute()
    
    # Final update of load position
    update_load_cube_position(anchor_cube, load_cube, anchor_connection_cubelet)


def animate_anchor_leg_with_load_tracking(anchor_cube, load_cube, anchor_connection_cubelet, target_extension, steps=20, frame_delay=0.05):
    """
    Animate the anchor's red leg extension while continuously updating the load cube position.
    This ensures smooth translation of the load cube.
    
    Args:
        anchor_cube: RubiksCube instance (anchor)
        load_cube: RubiksCube instance (load)
        anchor_connection_cubelet: The specific CornerCubelet object with connection leg
        target_extension: Target extension in mm
        steps: Number of animation steps
        frame_delay: Delay between frames in seconds
    """
    import time
    
    start_extension = anchor_connection_cubelet.leg.extension
    delta = (target_extension - start_extension) / steps
    
    for step in range(steps):
        new_extension = start_extension + delta * (step + 1)
        anchor_connection_cubelet.leg.set_extension(new_extension)
        
        # Update load cube position at each step for smooth tracking
        update_load_cube_position(anchor_cube, load_cube, anchor_connection_cubelet)
        
        anchor_cube.doc.recompute()
        App.Gui.updateGui()
        time.sleep(frame_delay)
    
    # Finalize
    anchor_connection_cubelet.leg.set_extension(target_extension)
    update_load_cube_position(anchor_cube, load_cube, anchor_connection_cubelet)
    anchor_cube.doc.recompute()


def run_legs_only_cycle(anchor_cube, load_cube, anchor_connection_cubelet, num_cycles=3):
    """
    Cycle with only connection leg extensions and retractions.
    Only moves the anchor cube's (1,1,1) leg and load cube's (-1,-1,-1) leg.
    
    Args:
        anchor_cube: RubiksCube instance (anchor)
        load_cube: RubiksCube instance (load)
        anchor_connection_cubelet: The specific CornerCubelet object with connection leg
        num_cycles: Number of extend/retract cycles
    """
    print(f"\n=== LEGS ONLY CYCLE ({num_cycles} extend/retract sequences) ===")
    
    for cycle in range(num_cycles):
        # Extend connection legs
        target = random.uniform(30.0, 40.0)
        
        print(f"  Cycle {cycle + 1}: Extending connection legs to {target:.1f}mm")
        # Extend anchor leg (1,1,1) - red leg with smooth load tracking
        animate_anchor_leg_with_load_tracking(anchor_cube, load_cube, anchor_connection_cubelet, target, steps=15, frame_delay=0.02)
        
        # Extend load leg (-1,-1,-1) - blue leg
        load_cube.animate_leg_extension((-1, -1, -1), target, steps=15, frame_delay=0.02)
        # No need to update position - load leg extension doesn't change connection geometry
        
        time.sleep(0.2)
        
        # Retract both connection legs back to 25mm (connection position)
        print(f"  Cycle {cycle + 1}: Retracting connection legs to 25mm")
        # Retract anchor leg with smooth load tracking
        animate_anchor_leg_with_load_tracking(anchor_cube, load_cube, anchor_connection_cubelet, LEG_EXTENSION_TO_MEET, steps=15, frame_delay=0.02)
        
        load_cube.animate_leg_extension((-1, -1, -1), LEG_EXTENSION_TO_MEET, steps=15, frame_delay=0.02)
        # No need to update position
        
        time.sleep(0.2)


def run_rotations_only_cycle(anchor_cube, load_cube, anchor_connection_cubelet, num_rotations=5):
    """
    Cycle with only face rotations, no leg extensions.
    Only rotates faces that contain the connection corner (1,1,1) for anchor.
    The load cube is whipped around as the anchor cube rotates.
    
    Args:
        anchor_cube: RubiksCube instance (anchor)
        load_cube: RubiksCube instance (load)
        anchor_connection_cubelet: The specific CornerCubelet object with connection leg
        num_rotations: Number of random face rotations
    """
    print(f"\n=== ROTATIONS ONLY CYCLE ({num_rotations} face turns) ===")
    # Only faces containing corner (1,1,1): R (x=1), U (y=1), F (z=1)
    affected_faces = ["R", "U", "F"]
    
    for move in range(num_rotations):
        face = random.choice(affected_faces)
        clockwise = random.choice([True, False])
        
        print(f"  Rotation {move + 1}: {face} {'CW' if clockwise else 'CCW'} on anchor cube")
        # Perform animated rotation with load tracking - slower (40 steps, 0.05s delay)
        _rotate_face_with_load_tracking(anchor_cube, load_cube, anchor_connection_cubelet, face, clockwise, steps=40, frame_delay=0.05)
        
        time.sleep(0.5)


def run_combined_cycle(anchor_cube, load_cube, anchor_connection_cubelet, num_moves=5):
    """
    Cycle with both face rotations AND connection leg extensions simultaneously.
    Only moves connection legs and rotates affected faces.
    
    Args:
        anchor_cube: RubiksCube instance (anchor)
        load_cube: RubiksCube instance (load)
        anchor_connection_cubelet: The specific CornerCubelet object with connection leg
        num_moves: Number of combined moves
    """
    print(f"\n=== COMBINED CYCLE ({num_moves} rotations with connection leg extensions) ===")
    # Only faces containing corner (1,1,1): R (x=1), U (y=1), F (z=1)
    affected_faces = ["R", "U", "F"]
    
    for move in range(num_moves):
        face = random.choice(affected_faces)
        clockwise = random.choice([True, False])
        
        # Connection leg extension on anchor
        target_extension = random.uniform(30.0, 40.0)
        leg_extensions = [((1, 1, 1), target_extension)]
        
        print(f"  Move {move + 1}: {face} {'CW' if clockwise else 'CCW'} + connection leg to {target_extension:.1f}mm")
        # Rotate anchor with leg extensions and load tracking
        _rotate_with_legs_and_load_tracking(anchor_cube, load_cube, anchor_connection_cubelet, face, clockwise, leg_extensions, steps=20, frame_delay=0.02)
        
        # Extend load leg to match
        load_cube.animate_leg_extension((-1, -1, -1), target_extension, steps=1, frame_delay=0.0)
        update_load_cube_position(anchor_cube, load_cube, anchor_connection_cubelet)
        
        time.sleep(0.1)




def run_infinite_animation_loop():
    """Run infinite animation loop with two connected cubes."""
    print("=" * 60)
    print("TWO CUBES ANIMATION - VERSION 3.0 - CUBELET TRACKING FIX")
    print("=" * 60)
    
    doc_name = "TwoCubes_OOP"
    
    # Create new document
    if App.ActiveDocument and App.ActiveDocument.Name == doc_name:
        App.closeDocument(doc_name)
    
    doc = App.newDocument(doc_name)
    
    print("Creating Anchor Cube...")
    # Create anchor cube at origin
    anchor_cube = RubiksCube("AnchorCube")
    anchor_cube.create_geometry(doc)
    
    # Store reference to the connection cubelet - this specific object will be tracked
    global _anchor_connection_cubelet
    _anchor_connection_cubelet = anchor_cube.corner_cubelets.get((1, 1, 1))
    
    # Color the connection leg red (keep at home position - 0mm extension)
    if _anchor_connection_cubelet and _anchor_connection_cubelet.leg.inner_rod_obj:
        _anchor_connection_cubelet.leg.inner_rod_obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0)  # Red
        # Leg stays at home position (0mm extension) - no set_extension call
    
    print("Creating Load Cube...")
    # Calculate load cube position (based on legs at home position)
    load_position = calculate_load_cube_position()
    
    # Create load cube
    load_cube = RubiksCube("LoadCube")
    load_cube.create_geometry(doc)
    load_cube.model_obj.Placement.Base = load_position
    
    # Color the connection leg blue (keep at home position - 0mm extension)
    load_corner = load_cube.corner_cubelets.get((-1, -1, -1))
    if load_corner and load_corner.leg.inner_rod_obj:
        load_corner.leg.inner_rod_obj.ViewObject.ShapeColor = (0.0, 0.0, 1.0)  # Blue
        # Leg stays at home position (0mm extension) - no set_extension call
    
    # Update load position based on actual leg state (both at home position)
    update_load_cube_position(anchor_cube, load_cube, _anchor_connection_cubelet)
    
    doc.recompute()
    
    # Fit all objects in view
    import FreeCADGui as Gui
    Gui.SendMsgToActiveView("ViewFit")
    
    print(f"\nAnchor cube center: {anchor_cube.model_obj.Placement.Base}")
    print(f"Load cube center: {load_cube.model_obj.Placement.Base}")
    print(f"Distance between centers: {load_position.Length:.1f}mm")
    print("\nInteractive animation mode - use dialog to control movements")
    
    # Create interactive dialog and store as global to prevent garbage collection
    global _animation_dialog
    _animation_dialog = AnimationControlDialog(anchor_cube, load_cube)
    _animation_dialog.show()



class AnimationControlDialog(QtGui.QDialog):
    """Dialog to control cube animations step by step."""
    
    def __init__(self, anchor_cube, load_cube):
        super(AnimationControlDialog, self).__init__()
        self.anchor_cube = anchor_cube
        self.load_cube = load_cube
        self.move_count = 0
        
        self.setWindowTitle("Two Cubes Animation Control")
        self.setModal(False)
        
        # Layout
        layout = QtGui.QVBoxLayout()
        
        # Info label
        self.info_label = QtGui.QLabel("Ready to animate")
        layout.addWidget(self.info_label)
        
        # Buttons
        btn_layout = QtGui.QHBoxLayout()
        
        self.btn_rotate = QtGui.QPushButton("Next Rotation")
        self.btn_rotate.clicked.connect(self.do_rotation)
        btn_layout.addWidget(self.btn_rotate)
        
        self.btn_leg = QtGui.QPushButton("Extend/Retract Red Leg")
        self.btn_leg.clicked.connect(self.do_leg_movement)
        btn_layout.addWidget(self.btn_leg)
        
        self.btn_blue_leg = QtGui.QPushButton("Extend/Retract Blue Leg")
        self.btn_blue_leg.clicked.connect(self.do_blue_leg_movement)
        btn_layout.addWidget(self.btn_blue_leg)
        
        layout.addLayout(btn_layout)
        
        # Close button
        self.btn_close = QtGui.QPushButton("Close")
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close)
        
        self.setLayout(layout)
    
    def do_rotation(self):
        """Perform one random face rotation."""
        affected_faces = ["R", "U", "F"]
        face = random.choice(affected_faces)
        clockwise = random.choice([True, False])
        
        self.move_count += 1
        self.info_label.setText(f"Move {self.move_count}: Rotating {face} {'CW' if clockwise else 'CCW'}...")
        self.btn_rotate.setEnabled(False)
        self.btn_leg.setEnabled(False)
        self.btn_blue_leg.setEnabled(False)
        QtGui.QApplication.processEvents()
        
        print(f"\n=== Move {self.move_count}: {face} {'CW' if clockwise else 'CCW'} ===")
        _rotate_face_with_load_tracking(self.anchor_cube, self.load_cube, _anchor_connection_cubelet, face, clockwise, steps=40, frame_delay=0.05)
        
        self.info_label.setText(f"Move {self.move_count} complete. Ready for next move.")
        self.btn_rotate.setEnabled(True)
        self.btn_leg.setEnabled(True)
        self.btn_blue_leg.setEnabled(True)
    
    def do_leg_movement(self):
        """Extend or retract the red leg."""
        if not _anchor_connection_cubelet:
            self.info_label.setText("ERROR: Anchor corner not found!")
            return
        
        current_ext = _anchor_connection_cubelet.leg.extension
        
        # Toggle between extended and home position (0mm)
        if current_ext <= 1.0:  # Close to home position
            target = random.uniform(35.0, 40.0)
            action = "Extending"
        else:
            target = 0.0  # Retract to home position
            action = "Retracting"
        
        self.move_count += 1
        self.info_label.setText(f"Move {self.move_count}: {action} red leg to {target:.1f}mm...")
        self.btn_rotate.setEnabled(False)
        self.btn_leg.setEnabled(False)
        self.btn_blue_leg.setEnabled(False)
        QtGui.QApplication.processEvents()
        
        print(f"\n=== Move {self.move_count}: {action} red leg to {target:.1f}mm ===")
        # Use smooth tracking function for continuous load cube translation
        animate_anchor_leg_with_load_tracking(self.anchor_cube, self.load_cube, _anchor_connection_cubelet, target, steps=20, frame_delay=0.05)
        
        self.info_label.setText(f"Move {self.move_count} complete. Ready for next move.")
        self.btn_rotate.setEnabled(True)
        self.btn_leg.setEnabled(True)
        self.btn_blue_leg.setEnabled(True)
    
    def do_blue_leg_movement(self):
        """Extend or retract the blue leg on the load cube, pushing it away from anchor."""
        load_corner = self.load_cube.corner_cubelets.get((-1, -1, -1))
        if not load_corner:
            self.info_label.setText("ERROR: Load corner not found!")
            return
        
        current_ext = load_corner.leg.extension
        
        # Toggle between extended and home position (0mm)
        if current_ext <= 1.0:  # Close to home position
            target = random.uniform(35.0, 40.0)
            action = "Extending"
        else:
            target = 0.0  # Retract to home position
            action = "Retracting"
        
        self.move_count += 1
        self.info_label.setText(f"Move {self.move_count}: {action} blue leg to {target:.1f}mm...")
        self.btn_rotate.setEnabled(False)
        self.btn_leg.setEnabled(False)
        self.btn_blue_leg.setEnabled(False)
        QtGui.QApplication.processEvents()
        
        print(f"\n=== Move {self.move_count}: {action} blue leg to {target:.1f}mm ===")
        
        # Animate blue leg extension with load cube translation (Newton's 3rd Law)
        start_extension = load_corner.leg.extension
        delta_ext = target - start_extension
        steps = 20
        frame_delay = 0.05
        
        # Get the push direction - opposite to the load cube's (-1,-1,-1) leg axis
        # When blue leg extends, it pushes the cube AWAY from anchor (opposite to leg direction)
        load_placement = self.load_cube.model_obj.Placement
        load_diagonal = App.Vector(-1, -1, -1)
        load_diagonal.normalize()
        push_direction = -load_placement.Rotation.multVec(load_diagonal)  # Negative for push away
        
        # Store initial position
        initial_position = App.Vector(load_placement.Base)
        
        for step in range(steps):
            # Update leg extension
            new_extension = start_extension + delta_ext * (step + 1) / steps
            load_corner.leg.set_extension(new_extension)
            
            # Push load cube away along the leg axis (Newton's 3rd Law)
            # The cube moves in the direction of the leg extension
            translation = push_direction * (new_extension - start_extension)
            self.load_cube.model_obj.Placement.Base = initial_position + translation
            
            self.load_cube.doc.recompute()
            App.Gui.updateGui()
            time.sleep(frame_delay)
        
        # Finalize
        load_corner.leg.set_extension(target)
        final_translation = push_direction * delta_ext
        self.load_cube.model_obj.Placement.Base = initial_position + final_translation
        self.load_cube.doc.recompute()
        
        self.info_label.setText(f"Move {self.move_count} complete. Ready for next move.")
        self.btn_rotate.setEnabled(True)
        self.btn_leg.setEnabled(True)
        self.btn_blue_leg.setEnabled(True)


if __name__ == "__main__":
    run_infinite_animation_loop()
