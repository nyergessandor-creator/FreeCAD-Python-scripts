"""
FreeCAD Script: Rubik's Cube Assembly with Telescoping Corner Legs
------------------------------------------------------------------
This script generates a 3x3x3 Rubik's Cube with:
- 1 spider core (fixed)
- 6 center pieces
- 12 edge pieces
- 8 corner pieces with telescoping legs (for inter-cube connections)

The telescoping legs on corners allow multiple cubes to connect and push
each other during rotations, similar to the three.js implementation.

Author: GitHub Copilot
"""

import FreeCAD as App
import Part
import math

# Constants
SPIDER_ROD_DIAMETER = 8.0
SPIDER_ROD_LENGTH = 82.0
CUBELET_SIZE = 25.0
GAP = 0.0  # No gap - cubelets touch for constraint-driven physics
SPACING = CUBELET_SIZE + GAP  # Distance from center to adjacent cubelet centers

# Corner leg parameters
LEG_OUTER_LENGTH = 30.0  # 30mm outer tube (shorter, more embedded)
LEG_OUTER_DIAMETER = 15.0  # 15mm diameter outer tube
LEG_INNER_LENGTH = 50.0  # 50mm inner rod (extends out)
LEG_INNER_DIAMETER = 10.0  # 10mm diameter inner rod
LEG_OVERLAP = 10.0  # How much inner rod stays inside outer tube at minimum extension


def create_component(doc, parent, name, shape, color):
    """Creates an App::Part inside a parent Part/Group"""
    # Create Container Part
    part_obj = doc.addObject("App::Part", name)
    
    # Add to parent logic (if parent is not None)
    if parent:
        parent.addObject(part_obj)
    
    # Create Body (Geometry) inside the Part
    feat = doc.addObject("Part::Feature", f"{name}_Geo")
    feat.Shape = shape
    feat.ViewObject.ShapeColor = color
    feat.ViewObject.Selectable = True
    part_obj.addObject(feat)
    
    # Make the Part container display mode show children so they're clickable
    if hasattr(part_obj.ViewObject, 'DisplayMode'):
        part_obj.ViewObject.DisplayMode = 'Group'
    
    return part_obj, feat


def create_leg_tip_marker(part, x, y, z):
    """
    No longer needed - tip marker is now built into the leg geometry itself.
    """
    pass


def create_corner_leg(x, y, z):
    """
    Creates a telescoping leg for a corner cubelet.
    Returns: (outer_tube_shape, diagonal_vector, tube_start_point, rod_start_point)
    The outer tube is fused with the cube.
    The inner rod will be created as a separate child object for animation.
    """
    # Diagonal direction (normalized) - make a copy to avoid mutation
    diagonal = App.Vector(x, y, z)
    diagonal.normalize()
    
    # OUTER TUBE (embedded in corner, hollow)
    outer_radius = LEG_OUTER_DIAMETER / 2
    inner_radius = LEG_INNER_DIAMETER / 2 + 0.5  # Slight clearance for sliding
    
    # Create outer cylinder
    outer_cyl = Part.makeCylinder(outer_radius, LEG_OUTER_LENGTH, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
    # Create inner hollow
    inner_hollow = Part.makeCylinder(inner_radius, LEG_OUTER_LENGTH, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
    # Make tube (hollow cylinder)
    outer_tube = outer_cyl.cut(inner_hollow)
    
    # Rotate to align with diagonal
    z_axis = App.Vector(0, 0, 1)
    rot_axis = z_axis.cross(diagonal)
    
    if rot_axis.Length > 0.001:  # Not parallel
        rot_axis.normalize()
        dot_product = max(-1.0, min(1.0, z_axis.dot(diagonal)))
        rot_angle = math.degrees(math.acos(dot_product))
        outer_tube.rotate(App.Vector(0, 0, 0), rot_axis, rot_angle)
    elif diagonal.z < 0:  # Opposite direction
        outer_tube.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 180)
    
    # Position leg embedded in corner - use multiplication operator to avoid mutation
    corner_point = App.Vector(x, y, z) * (CUBELET_SIZE / 2)
    inward_offset = diagonal * (-LEG_OUTER_LENGTH / 2)
    tube_start_point = corner_point + inward_offset
    
    outer_tube.translate(tube_start_point)
    
    # Inner rod starts at the outer end of the tube, overlapping by LEG_OVERLAP
    # It extends outward along the diagonal
    # Add 3mm extension so tip is visible
    rod_start_point = tube_start_point + diagonal * (LEG_OUTER_LENGTH - LEG_OVERLAP + 3)
    
    return outer_tube, diagonal, tube_start_point, rod_start_point


def get_corner_color(x, y, z, normal):
    """
    Determines the color for a leg face based on which cube face it's closest to.
    """
    colors = {
        'X+': (0.9, 0.5, 0.5),  # Red
        'X-': (0.9, 0.5, 0.5),  # Red/Orange
        'Y+': (0.5, 0.5, 0.9),  # Blue/White
        'Y-': (0.5, 0.5, 0.9),  # Blue/Yellow
        'Z+': (0.5, 0.9, 0.5),  # Green
        'Z-': (0.5, 0.9, 0.5),  # Green/Blue
    }
    
    best_dot = -float('inf')
    best_color = (0.9, 0.9, 0.5)
    
    # Check alignment with each axis
    for axis_name, axis_vec, color in [
        ('X+', App.Vector(x, 0, 0), colors['X+']),
        ('Y+', App.Vector(0, y, 0), colors['Y+']),
        ('Z+', App.Vector(0, 0, z), colors['Z+']),
    ]:
        dot = normal.dot(axis_vec)
        if dot > best_dot:
            best_dot = dot
            best_color = color
    
    return best_color


def create_mating_plane(part, face_direction, name):
    """
    Removed - no longer creating mating markers on regular cubelet faces.
    Only corner leg tips will have markers for inter-cube connections.
    """
    pass


def get_adjacent_faces(x, y, z):
    """
    Returns empty list - we're not adding face markers anymore.
    Only corners get leg tip markers.
    """
    return []
    if x == 0:
        faces.append('X+')
        faces.append('X-')
    if y == 0:
        faces.append('Y+')
        faces.append('Y-')
    if z == 0:
        faces.append('Z+')
        faces.append('Z-')
    
    return faces


def generate_assembly():
    doc_name = "MagicCube_Assembly_Constraints"
    
    # Clear report view
    if hasattr(App, 'Console'):
        try:
            from PySide import QtGui
            mw = QtGui.QApplication.activeWindow()
            if mw:
                for widget in mw.findChildren(QtGui.QTextEdit):
                    if widget.objectName() == "Report view":
                        widget.clear()
                        break
        except:
            pass  # Silently fail if can't clear
    
    print(f"Starting assembly generation...")
    print(f"Checking for existing document '{doc_name}'...")
    
    # Force close any existing document without saving
    for doc_check in list(App.listDocuments().keys()):
        if doc_check == doc_name:
            print(f"Closing existing document '{doc_name}' without saving")
            App.closeDocument(doc_name)
            break
    
    print(f"Creating new document '{doc_name}'...")
    doc = App.newDocument(doc_name)
    
    # Create Root Assembly Container
    print(f"Creating root Model container...")
    root_model = doc.addObject("App::Part", "Model")
    
    print(f"Generating Rubik's Cube with constraints...")
    print(f"SPACING = {SPACING}mm, CUBELET_SIZE = {CUBELET_SIZE}mm, GAP = {GAP}mm")
    
    # Store all cubelet parts and their grid positions
    cubelets = {}  # key: (x, y, z), value: part object
    
    # =========================================================================
    # 1. SPIDER (The Core) - Fixed
    # =========================================================================
    
    print("Creating spider core...")
    x_rod = Part.makeCylinder(SPIDER_ROD_DIAMETER/2, SPIDER_ROD_LENGTH, 
                               App.Vector(-SPIDER_ROD_LENGTH/2, 0, 0), App.Vector(1,0,0))
    y_rod = Part.makeCylinder(SPIDER_ROD_DIAMETER/2, SPIDER_ROD_LENGTH, 
                               App.Vector(0, -SPIDER_ROD_LENGTH/2, 0), App.Vector(0,1,0))
    z_rod = Part.makeCylinder(SPIDER_ROD_DIAMETER/2, SPIDER_ROD_LENGTH, 
                               App.Vector(0, 0, -SPIDER_ROD_LENGTH/2), App.Vector(0,0,1))
    center_sphere = Part.makeSphere(13.0, App.Vector(0,0,0))
    
    spider_shape = Part.makeCompound([x_rod, y_rod, z_rod]).fuse(center_sphere)
    spider_part, _ = create_component(doc, root_model, "Spider", spider_shape, (0.3, 0.3, 0.3))
    print(f"Spider created: {spider_part.Name}")
    
    # =========================================================================
    # 2. CREATE ALL CUBELETS
    # =========================================================================
    
    print("\nCreating center pieces...")
    # Centers (6 pieces)
    center_positions = [
        (1, 0, 0, 'R', (0.9, 0.5, 0.5)),   # Right
        (-1, 0, 0, 'L', (0.9, 0.5, 0.5)),  # Left
        (0, 1, 0, 'U', (0.5, 0.5, 0.9)),   # Up
        (0, -1, 0, 'D', (0.5, 0.5, 0.9)),  # Down
        (0, 0, 1, 'F', (0.5, 0.9, 0.5)),   # Front
        (0, 0, -1, 'B', (0.5, 0.9, 0.5)),  # Back
    ]
    
    for x, y, z, face, color in center_positions:
        shape = Part.makeBox(CUBELET_SIZE, CUBELET_SIZE, CUBELET_SIZE, 
                             App.Vector(-CUBELET_SIZE/2, -CUBELET_SIZE/2, -CUBELET_SIZE/2))
        
        part, geo = create_component(doc, root_model, f"Center_{face}", shape, color)
        part.Placement.Base = App.Vector(x * SPACING, y * SPACING, z * SPACING)
        
        # Store in dictionary
        cubelets[(x, y, z)] = part
    
    print(f"Created {len([p for p in center_positions])} center pieces")
    
    # Edges (12 pieces)
    print("\nCreating edge pieces...")
    edge_positions = [
        (1, 1, 0, "RU"), (1, -1, 0, "RD"),
        (-1, 1, 0, "LU"), (-1, -1, 0, "LD"),
        (1, 0, 1, "RF"), (1, 0, -1, "RB"),
        (-1, 0, 1, "LF"), (-1, 0, -1, "LB"),
        (0, 1, 1, "UF"), (0, 1, -1, "UB"),
        (0, -1, 1, "DF"), (0, -1, -1, "DB"),
    ]
    
    for x, y, z, name in edge_positions:
        shape = Part.makeBox(CUBELET_SIZE, CUBELET_SIZE, CUBELET_SIZE, 
                             App.Vector(-CUBELET_SIZE/2, -CUBELET_SIZE/2, -CUBELET_SIZE/2))
        part, geo = create_component(doc, root_model, f"Edge_{name}", shape, (0.6, 0.6, 0.6))
        part.Placement.Base = App.Vector(x * SPACING, y * SPACING, z * SPACING)
        
        cubelets[(x, y, z)] = part
    
    print(f"Created {len(edge_positions)} edge pieces")
    
    # Corners (8 pieces)
    print("\nCreating corner pieces...")
    corner_positions = [
        (1, 1, 1, "RUF"), (1, 1, -1, "RUB"),
        (1, -1, 1, "RDF"), (1, -1, -1, "RDB"),
        (-1, 1, 1, "LUF"), (-1, 1, -1, "LUB"),
        (-1, -1, 1, "LDF"), (-1, -1, -1, "LDB"),
    ]
    
    for x, y, z, name in corner_positions:
        # Create basic cube
        cube_shape = Part.makeBox(CUBELET_SIZE, CUBELET_SIZE, CUBELET_SIZE, 
                                   App.Vector(-CUBELET_SIZE/2, -CUBELET_SIZE/2, -CUBELET_SIZE/2))
        
        # Create telescoping leg outer tube
        outer_tube, diagonal, tube_start, rod_start = create_corner_leg(x, y, z)
        
        # Combine cube and outer tube only
        combined_shape = cube_shape.fuse(outer_tube)
        
        part, geo = create_component(doc, root_model, f"Corner_{name}", combined_shape, (0.9, 0.9, 0.5))
        parent_pos = App.Vector(x * SPACING, y * SPACING, z * SPACING)
        part.Placement.Base = parent_pos
        
        # Store leg info as properties for animation
        part.addProperty("App::PropertyVector", "LegDiagonal", "Telescoping", "Leg direction vector")
        part.addProperty("App::PropertyVector", "LegStart", "Telescoping", "Leg start point in local coords")
        part.addProperty("App::PropertyFloat", "LegExtension", "Telescoping", "Current leg extension (0-30mm)")
        part.addProperty("App::PropertyFloat", "LegTargetExtension", "Telescoping", "Target extension this leg is moving toward")
        part.addProperty("App::PropertyFloat", "LegSpeed", "Telescoping", "Speed in mm per rotation cycle")
        part.LegDiagonal = diagonal
        # Convert rod_start from world coords to parent local coords
        part.LegStart = rod_start.sub(parent_pos)
        part.LegExtension = 0.0  # Start retracted
        part.LegTargetExtension = 0.0  # No movement yet
        part.LegSpeed = 0.0  # Will be set when movement starts
        
        # Create INNER ROD as a separate child object (so it can be animated)
        inner_rod = Part.makeCylinder(LEG_INNER_DIAMETER / 2, LEG_INNER_LENGTH,
                                       App.Vector(0, 0, 0), App.Vector(0, 0, 1))
        
        # TIP MARKER - sphere at the end of inner rod
        tip_sphere = Part.makeSphere(LEG_INNER_DIAMETER / 2, App.Vector(0, 0, LEG_INNER_LENGTH))
        inner_rod_with_tip = inner_rod.fuse(tip_sphere)
        
        # Create the inner rod as a child Part::Feature
        inner_rod_obj = doc.addObject("Part::Feature", f"InnerRod_{name}")
        inner_rod_obj.Shape = inner_rod_with_tip
        inner_rod_obj.ViewObject.ShapeColor = (1.0, 1.0, 0.0)  # Yellow
        inner_rod_obj.ViewObject.Selectable = True
        part.addObject(inner_rod_obj)
        
        # Position should be rod_start (already in world coords), minus parent_pos to get local
        inner_rod_local_pos = rod_start.sub(parent_pos)
        
        # For debugging: print the calculated values
        print(f"\n{name}: parent_pos={parent_pos}, diagonal={diagonal}")
        print(f"  rod_start (world)={rod_start}, local_pos={inner_rod_local_pos}")
        
        # Use the SAME rotation logic that worked for outer_tube
        z_axis = App.Vector(0, 0, 1)
        rot_axis = z_axis.cross(diagonal)
        
        if rot_axis.Length > 0.001:
            rot_axis.normalize()
            dot_product = max(-1.0, min(1.0, z_axis.dot(diagonal)))
            rot_angle = math.degrees(math.acos(dot_product))
            print(f"  rot_axis={rot_axis}, rot_angle={rot_angle}")
            rotation = App.Rotation(rot_axis, rot_angle)
            inner_rod_obj.Placement = App.Placement(inner_rod_local_pos, rotation)
        elif diagonal.z < 0:
            rotation = App.Rotation(App.Vector(1, 0, 0), 180.0)
            inner_rod_obj.Placement = App.Placement(inner_rod_local_pos, rotation)
        else:
            inner_rod_obj.Placement = App.Placement(inner_rod_local_pos, App.Rotation())
        
        cubelets[(x, y, z)] = part
    
    print(f"Created {len(corner_positions)} corner pieces with telescoping legs")
    
    print("\nRecomputing document...")
    doc.recompute()
    
    # =========================================================================
    # 3. NOTES ON INTER-CUBE CONSTRAINTS
    # =========================================================================
    
    print("\nCorner pieces have telescoping legs for inter-cube connections.")
    print("Yellow markers at leg tips indicate mating points between cubes.")
    print("\nTo connect multiple cubes:")
    print("1. Create multiple cube instances")
    print("2. Position them so leg tips of one cube touch leg tips of another")
    print("3. Add constraints between the leg tip markers")
    print("4. Rotating one cube's face will push the connected cube")
    
    # =========================================================================
    # Store metadata for animation
    # =========================================================================
    
    # Add custom properties to track grid positions
    for (x, y, z), part in cubelets.items():
        part.addProperty("App::PropertyInteger", "GridX", "GridPosition", "X position in 3x3x3 grid")
        part.addProperty("App::PropertyInteger", "GridY", "GridPosition", "Y position in 3x3x3 grid")
        part.addProperty("App::PropertyInteger", "GridZ", "GridPosition", "Z position in 3x3x3 grid")
        part.GridX = x
        part.GridY = y
        part.GridZ = z
        
        # Tip markers are now built into the leg geometry
    
    print(f"Created {len(corner_positions)} corner pieces with telescoping legs")
    if hasattr(App, 'Gui'):
        import FreeCADGui as Gui
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.SendMsgToActiveView("ViewFit")
    
    print(f"\nRubik's Cube with {len(cubelets)} cubelets created successfully!")
    print(f"Document: '{doc_name}'")
    return doc


if __name__ == "__main__":
    generate_assembly()
