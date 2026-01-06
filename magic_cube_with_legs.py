"""
FreeCAD Script: Constraints-Based Magic Cube with Telescoping Legs

This script creates a self-reconfigurable modular robotics system with:
- A spider structure (three orthogonal rods as the rigid central frame)
- Cubelets with spherical and revolute constraints
- Eight telescoping legs at corners with prismatic joints

Author: Sandor Nyerges
Date: January 5, 2026
"""

import FreeCAD as App
import Part
import math

# Try to import Assembly3 or Assembly4 for joints
try:
    import asm3
    HAS_ASM3 = True
    HAS_ASM4 = False
except ImportError:
    HAS_ASM3 = False
    try:
        import Assembly4 as asm4
        HAS_ASM4 = True
    except ImportError:
        HAS_ASM4 = False

# If no assembly workbench, we'll use groups for animation
ASSEMBLY_AVAILABLE = HAS_ASM3 or HAS_ASM4

# Constants - dimensions in mm
SPIDER_ROD_DIAMETER = 8     # mm
SPIDER_ROD_LENGTH = 82      # mm
CUBELET_SIZE = 25           # mm
LEG_INNER_LENGTH = 75        # mm
LEG_INNER_DIAMETER = 10     # mm for inner telescoping part
LEG_OUTER_DIAMETER = 18     # mm for outer telescoping part
LEG_OUTER_LENGTH = LEG_INNER_LENGTH  # Each leg has two telescoping parts
LEG_OFFSET = 20             # mm to move legs away from corners

def create_spider():
    """
    Create the spider structure - three orthogonal rods intersecting at origin.
    Returns a compound shape.
    """
    print("Creating spider structure...")
    
    # Create three cylinders along X, Y, and Z axes
    rod_radius = SPIDER_ROD_DIAMETER / 2
    
    # X-axis rod (red in visualization)
    x_rod = Part.makeCylinder(
        rod_radius, 
        SPIDER_ROD_LENGTH, 
        App.Vector(-SPIDER_ROD_LENGTH/2, 0, 0),
        App.Vector(1, 0, 0)
    )
    
    # Y-axis rod (green in visualization)
    y_rod = Part.makeCylinder(
        rod_radius,
        SPIDER_ROD_LENGTH,
        App.Vector(0, -SPIDER_ROD_LENGTH/2, 0),
        App.Vector(0, 1, 0)
    )
    
    # Z-axis rod (blue in visualization)
    z_rod = Part.makeCylinder(
        rod_radius,
        SPIDER_ROD_LENGTH,
        App.Vector(0, 0, -SPIDER_ROD_LENGTH/2),
        App.Vector(0, 0, 1)
    )
    
    # Create central sphere at origin for constraint attachment
    central_sphere = Part.makeSphere(13.0, App.Vector(0, 0, 0))  # 10mm diameter
    
    # Combine all three rods and fuse with central sphere
    spider_compound = Part.makeCompound([x_rod, y_rod, z_rod])
    spider = spider_compound.fuse(central_sphere)
    
    return spider

def create_cubelet(position, cubelet_type="center", color=(0.8, 0.8, 0.8)):
    """
    Create a single cubelet at the specified position.
    
    Args:
        position: App.Vector for cubelet center
        cubelet_type: "center", "edge", or "corner"
        color: RGB tuple for visualization
    
    Returns:
        Part.Shape of the cubelet
    """
    # Create a cube
    cube = Part.makeBox(
        CUBELET_SIZE,
        CUBELET_SIZE,
        CUBELET_SIZE,
        App.Vector(
            position.x - CUBELET_SIZE/2,
            position.y - CUBELET_SIZE/2,
            position.z - CUBELET_SIZE/2
        )
    )
    
    return cube

def create_telescoping_leg(corner_position, direction):
    """
    Create a telescoping leg with two parts (inner and outer).
    
    Args:
        corner_position: App.Vector for the corner where leg starts
        direction: App.Vector (normalized) for leg direction
    
    Returns:
        Tuple of (inner_leg, outer_leg) Part.Shape objects
    """
    # Normalize direction
    dir_normalized = direction.normalize()
    
    # Outer leg (fixed to corner) - offset by LEG_OFFSET from corner
    outer_start = corner_position + dir_normalized.multiply(LEG_OFFSET)
    outer_leg = Part.makeCylinder(
        LEG_OUTER_DIAMETER / 2,
        LEG_OUTER_LENGTH,
        outer_start,
        dir_normalized
    )
    
    # Inner leg (telescoping part)
    inner_start = outer_start +dir_normalized
    inner_leg = Part.makeCylinder(
        LEG_INNER_DIAMETER / 2,
        LEG_INNER_LENGTH,
        inner_start,
        dir_normalized
    )
    
    return (outer_leg, inner_leg)

def create_magic_cube():
    """
    Create the complete magic cube assembly with spider, cubelets, and legs.
    Returns a dictionary with references to all objects for animation.
    """
    print("Starting magic cube creation...")
    
    # Create document
    doc = App.ActiveDocument
    if doc is None:
        doc = App.newDocument("MagicCube")
    
    # Dictionary to store object references
    cube_objects = {
        'spider': None,
        'centers': {},  # Keyed by face: 'R', 'L', 'U', 'D', 'F', 'B'
        'edges': {},
        'corners': {},
        'legs': []
    }
    
    # Create spider structure
    spider_shape = create_spider()
    spider_obj = doc.addObject("Part::Feature", "Spider")
    spider_obj.Shape = spider_shape
    spider_obj.ViewObject.ShapeColor = (0.7, 0.7, 0.7)
    cube_objects['spider'] = spider_obj
    print("Spider created")
    
    # Define 3x3x3 cube positions
    # Center cubelets (6 faces)
    spacing = CUBELET_SIZE * 1.0  # Small gap between cubelets
    
    # Map center positions to face names (Rubik's cube notation)
    # R=Right, L=Left, U=Up, D=Down, F=Front, B=Back
    center_positions = {
        'R': App.Vector(spacing, 0, 0),   # +X face (Right)
        'L': App.Vector(-spacing, 0, 0),  # -X face (Left)
        'U': App.Vector(0, spacing, 0),   # +Y face (Up)
        'D': App.Vector(0, -spacing, 0),  # -Y face (Down)
        'F': App.Vector(0, 0, spacing),   # +Z face (Front)
        'B': App.Vector(0, 0, -spacing),  # -Z face (Back)
    }
    
    # Create center cubelets
    for face_name, pos in center_positions.items():
        cubelet = create_cubelet(pos, "center", (0.9, 0.5, 0.5))
        obj = doc.addObject("Part::Feature", f"Center_{face_name}")
        obj.Shape = cubelet
        obj.ViewObject.ShapeColor = (0.9, 0.5, 0.5)
        # Store original position for accurate rotation gathering
        obj.Label2 = f"{pos.x},{pos.y},{pos.z}"
        cube_objects['centers'][face_name] = obj
    print("Center cubelets created")
    
    # Edge cubelets (12 edges)
    edge_positions = [
        # Edges parallel to Z (around Z axis)
        ("RU", App.Vector(spacing, spacing, 0)),
        ("RD", App.Vector(spacing, -spacing, 0)),
        ("LU", App.Vector(-spacing, spacing, 0)),
        ("LD", App.Vector(-spacing, -spacing, 0)),
        # Edges parallel to Y (around Y axis)
        ("RF", App.Vector(spacing, 0, spacing)),
        ("RB", App.Vector(spacing, 0, -spacing)),
        ("LF", App.Vector(-spacing, 0, spacing)),
        ("LB", App.Vector(-spacing, 0, -spacing)),
        # Edges parallel to X (around X axis)
        ("UF", App.Vector(0, spacing, spacing)),
        ("UB", App.Vector(0, spacing, -spacing)),
        ("DF", App.Vector(0, -spacing, spacing)),
        ("DB", App.Vector(0, -spacing, -spacing)),
    ]
    
    # Create edge cubelets
    for edge_name, pos in edge_positions:
        cubelet = create_cubelet(pos, "edge", (0.5, 0.9, 0.5))
        obj = doc.addObject("Part::Feature", f"Edge_{edge_name}")
        obj.Shape = cubelet
        obj.ViewObject.ShapeColor = (0.5, 0.9, 0.5)
        # Store original position for accurate rotation gathering
        obj.Label2 = f"{pos.x},{pos.y},{pos.z}"
        cube_objects['edges'][edge_name] = obj
    print("Edge cubelets created")
    
    # Corner cubelets (8 corners) with telescoping legs
    corner_positions = [
        ("RUF", App.Vector(spacing, spacing, spacing)),
        ("RUB", App.Vector(spacing, spacing, -spacing)),
        ("RDF", App.Vector(spacing, -spacing, spacing)),
        ("RDB", App.Vector(spacing, -spacing, -spacing)),
        ("LUF", App.Vector(-spacing, spacing, spacing)),
        ("LUB", App.Vector(-spacing, spacing, -spacing)),
        ("LDF", App.Vector(-spacing, -spacing, spacing)),
        ("LDB", App.Vector(-spacing, -spacing, -spacing)),
    ]
    
    # Create corner cubelets with FUSED outer legs
    for corner_name, pos in corner_positions:
        # IMPORTANT: Store original position BEFORE any operations that might modify it
        original_pos = App.Vector(pos.x, pos.y, pos.z)  # Make a copy!
        
        print(f"Creating corner {corner_name} at position ({pos.x}, {pos.y}, {pos.z})")
        
        # Create the basic cubelet
        cubelet = create_cubelet(pos, "corner", (0.5, 0.5, 0.9))
        
        # Create telescoping legs
        leg_direction = pos.normalize()  # This might modify pos!
        outer_leg, inner_leg = create_telescoping_leg(pos, leg_direction)
        
        # FUSE outer leg into the cubelet (they move together as one unit)
        # Use fuse() which creates a proper solid, not a compound
        corner_with_outer_leg = cubelet.fuse(outer_leg)
        
        # Create corner object with fused outer leg
        obj = doc.addObject("Part::Feature", f"Corner_{corner_name}")
        obj.Shape = corner_with_outer_leg
        obj.ViewObject.ShapeColor = (0.5, 0.5, 0.9)
        cube_objects['corners'][corner_name] = obj
        
        # Store the ORIGINAL corner position (not the modified one!)
        position_string = f"{original_pos.x},{original_pos.y},{original_pos.z}"
        obj.Label2 = position_string
        print(f"  Stored Label2: '{position_string}'")
        
        # Create SEPARATE inner leg object for telescoping
        inner_obj = doc.addObject("Part::Feature", f"InnerLeg_{corner_name}")
        inner_obj.Shape = inner_leg
        inner_obj.ViewObject.ShapeColor = (0.9, 0.7, 0.3)
        
        # Store leg association with corner
        cube_objects['legs'].append({
            'corner': corner_name,
            'corner_obj': obj,
            'inner': inner_obj,
            'direction': leg_direction  # Store for telescoping
        })
    print(f"Corner cubelets created (outer legs fused, {len(cube_objects['legs'])} inner legs separate)")
    
    # No separate leg objects needed - they're part of corners now!
    print("Legs are now fused into corner cubelets")
    
    # Recompute document
    doc.recompute()
    
    print("\n" + "="*60)
    print("Magic Cube Creation Complete!")
    print("="*60)
    print("\nStructure created:")
    print("  - 1 Spider (static central frame)")
    print("  - 6 Center cubelets (red)")
    print("  - 12 Edge cubelets (green)")
    print("  - 8 Corner cubelets (blue) with FUSED outer legs")
    print("  - 8 Inner leg segments (separate for telescoping)")
    print("\nNote: Outer legs are fused into corners (move as one unit).")
    print("      Inner legs are separate and can telescope in/out.")
    print(f"\nAssembly workbench available: {ASSEMBLY_AVAILABLE}")
    print("\nNext steps for constraints:")
    print("  1. Center cubelets → Spider: Spherical constraints")
    print("  2. Edge/Corner cubelets → Centers: Revolute constraints")
    if not ASSEMBLY_AVAILABLE:
        print("\nNote: Assembly3/4 not available. Using simple rotation animation.")
    print("="*60)
    
    return cube_objects


def get_face_cubelets(face, cube_objects):
    """
    Get all cubelets that belong to a specific face for rotation.
    
    Args:
        face: One of 'R', 'L', 'U', 'D', 'F', 'B'
        cube_objects: Dictionary returned by create_magic_cube
    
    Returns:
        List of cubelet objects that are part of this face
    """
    face_map = {
        'R': {  # Right face (+X)
            'centers': ['R'],
            'edges': ['RU', 'RD', 'RF', 'RB'],
            'corners': ['RUF', 'RUB', 'RDF', 'RDB']
        },
        'L': {  # Left face (-X)
            'centers': ['L'],
            'edges': ['LU', 'LD', 'LF', 'LB'],
            'corners': ['LUF', 'LUB', 'LDF', 'LDB']
        },
        'U': {  # Up face (+Y)
            'centers': ['U'],
            'edges': ['RU', 'LU', 'UF', 'UB'],
            'corners': ['RUF', 'RUB', 'LUF', 'LUB']
        },
        'D': {  # Down face (-Y)
            'centers': ['D'],
            'edges': ['RD', 'LD', 'DF', 'DB'],
            'corners': ['RDF', 'RDB', 'LDF', 'LDB']
        },
        'F': {  # Front face (+Z)
            'centers': ['F'],
            'edges': ['RF', 'LF', 'UF', 'DF'],
            'corners': ['RUF', 'RDF', 'LUF', 'LDF']
        },
        'B': {  # Back face (-Z)
            'centers': ['B'],
            'edges': ['RB', 'LB', 'UB', 'DB'],
            'corners': ['RUB', 'RDB', 'LUB', 'LDB']
        }
    }
    
    if face not in face_map:
        return []
    
    cubelets = []
    face_data = face_map[face]
    
    # Add centers
    for center_name in face_data['centers']:
        if center_name in cube_objects['centers']:
            cubelets.append(cube_objects['centers'][center_name])
    
    # Add edges
    for edge_name in face_data['edges']:
        if edge_name in cube_objects['edges']:
            cubelets.append(cube_objects['edges'][edge_name])
    
    # Add corners
    for corner_name in face_data['corners']:
        if corner_name in cube_objects['corners']:
            cubelets.append(cube_objects['corners'][corner_name])
    
    return cubelets


def get_face_axis(face):
    """
    Get the rotation axis for a face.
    
    Returns:
        Tuple of (axis_vector, center_point)
    """
    axes = {
        'R': (App.Vector(1, 0, 0), App.Vector(CUBELET_SIZE, 0, 0)),
        'L': (App.Vector(1, 0, 0), App.Vector(-CUBELET_SIZE, 0, 0)),
        'U': (App.Vector(0, 1, 0), App.Vector(0, CUBELET_SIZE, 0)),
        'D': (App.Vector(0, 1, 0), App.Vector(0, -CUBELET_SIZE, 0)),
        'F': (App.Vector(0, 0, 1), App.Vector(0, 0, CUBELET_SIZE)),
        'B': (App.Vector(0, 0, 1), App.Vector(0, 0, -CUBELET_SIZE)),
    }
    return axes.get(face, (App.Vector(0, 0, 1), App.Vector(0, 0, 0)))

# Main execution
if __name__ == "__main__":
    try:
        cube_objects = create_magic_cube()
        print("\nSuccess! View the model in FreeCAD.")
        print("To animate, run the 'animate_magic_cube.py' script")
    except Exception as e:
        print(f"\nError creating magic cube: {str(e)}")
        import traceback
        traceback.print_exc()
