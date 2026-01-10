"""
Single Rubik's Cube using OOP approach - setup only
"""
import FreeCAD as App
import Part
import math

# Constants
CUBELET_SIZE = 25.0
SPACING = 25.0
GAP = 0.0
LEG_OUTER_DIAMETER = 12.0
LEG_OUTER_LENGTH = 30.0
LEG_INNER_DIAMETER = 10.0
LEG_INNER_LENGTH = 50.0
LEG_OVERLAP = 10.0


class TelescopingLeg:
    """Represents a telescoping leg attached to a corner cubelet."""
    
    def __init__(self, corner_position, diagonal, parent_cubelet):
        """
        Initialize a telescoping leg.
        
        Args:
            corner_position: (x, y, z) grid position of the corner (-1, 0, or 1)
            diagonal: Normalized direction vector
            parent_cubelet: The CornerCubelet object this leg belongs to
        """
        self.corner_position = corner_position
        self.diagonal = App.Vector(diagonal[0], diagonal[1], diagonal[2])
        self.diagonal.normalize()
        self.parent_cubelet = parent_cubelet
        self.extension = 0.0  # Current extension in mm (0-30)
        self.target_extension = 0.0
        
        # Geometry calculations
        corner_point = App.Vector(corner_position[0], corner_position[1], corner_position[2]) * (CUBELET_SIZE / 2)
        
        # Tube geometry
        self.tube_start_local = corner_point - self.diagonal * (LEG_OUTER_LENGTH / 2)
        
        # Rod geometry: starts at outer end of tube, with overlap and extension
        self.rod_start_local = self.tube_start_local + self.diagonal * (LEG_OUTER_LENGTH - LEG_OVERLAP + 3)
        
        # FreeCAD objects (set during creation)
        self.outer_tube_shape = None
        self.inner_rod_obj = None
    
    def get_base_rod_start(self):
        """Get the starting point of the inner rod in local coordinates."""
        return self.rod_start_local
    
    def get_tip_position_local(self):
        """
        Get the tip position (sphere surface) in local cubelet coordinates.
        Accounts for current extension.
        
        Returns:
            App.Vector: Tip position in local coords
        """
        # Rod starts at rod_start_local
        # Sphere center is at rod_start + 50mm (rod length)
        # Sphere surface is at center + 5mm (radius)
        # Plus current extension
        sphere_center_offset = LEG_INNER_LENGTH + self.extension
        sphere_surface_offset = sphere_center_offset + (LEG_INNER_DIAMETER / 2)
        
        return self.rod_start_local + self.diagonal * sphere_surface_offset
    
    def get_tip_position_world(self):
        """
        Get the tip position (sphere surface) in world coordinates.
        Accounts for cubelet position, cube rotation, and current extension.
        
        Returns:
            App.Vector: Tip position in world coords
        """
        # Get cubelet's world placement
        cubelet_placement = self.parent_cubelet.part_obj.getGlobalPlacement()
        tip_local = self.get_tip_position_local()
        
        # Transform through cubelet's rotation and position
        tip_rotated = cubelet_placement.Rotation.multVec(tip_local)
        tip_world = cubelet_placement.Base + tip_rotated
        
        return tip_world
    
    def set_extension(self, extension_mm):
        """
        Set the leg extension and update the visual geometry.
        
        Args:
            extension_mm: Extension amount in mm (0-30)
        """
        extension_mm = max(0.0, min(30.0, extension_mm))  # Clamp to valid range
        self.extension = extension_mm
        
        # Update the inner rod position in FreeCAD
        if self.inner_rod_obj:
            # The rod was positioned at base position, now translate by extension
            # Keep the rotation, just update the Base
            current_rotation = self.inner_rod_obj.Placement.Rotation
            new_base = self.rod_start_local + self.diagonal * extension_mm
            self.inner_rod_obj.Placement = App.Placement(new_base, current_rotation)


class CornerCubelet:
    """Represents a corner cubelet with a telescoping leg."""
    
    def __init__(self, grid_position, name_prefix="Corner"):
        """
        Initialize a corner cubelet.
        
        Args:
            grid_position: (x, y, z) tuple with values in {-1, 1}
            name_prefix: Prefix for FreeCAD object names
        """
        self.grid_position = grid_position
        self.name_prefix = name_prefix
        self.part_obj = None  # FreeCAD Part object
        self.leg = TelescopingLeg(grid_position, grid_position, self)
        
        # Position code (like "RUF" for Right-Up-Front)
        self.position_code = self._get_position_code()
    
    def _get_position_code(self):
        """Generate position code like 'RUF' from grid position."""
        x, y, z = self.grid_position
        code = ""
        code += "R" if x > 0 else "L"
        code += "U" if y > 0 else "D"
        code += "F" if z > 0 else "B"
        return code
    
    def create_geometry(self, doc, root_model):
        """
        Create the FreeCAD geometry for this cubelet.
        
        Args:
            doc: FreeCAD document
            root_model: Parent App::Part to add this to
        """
        x, y, z = self.grid_position
        
        # Create basic cube shape
        cube_shape = Part.makeBox(CUBELET_SIZE, CUBELET_SIZE, CUBELET_SIZE,
                                   App.Vector(-CUBELET_SIZE/2, -CUBELET_SIZE/2, -CUBELET_SIZE/2))
        
        # Create outer tube for leg
        outer_tube_shape = self._create_outer_tube()
        combined_shape = cube_shape.fuse(outer_tube_shape)
        
        # Create Part object
        self.part_obj = doc.addObject("App::Part", f"{self.name_prefix}_{self.position_code}")
        geo = doc.addObject("Part::Feature", f"{self.name_prefix}_{self.position_code}_Geo")
        geo.Shape = combined_shape
        geo.ViewObject.ShapeColor = (0.9, 0.9, 0.5)
        self.part_obj.addObject(geo)
        root_model.addObject(self.part_obj)
        
        # Position the cubelet
        self.part_obj.Placement.Base = App.Vector(x * SPACING, y * SPACING, z * SPACING)
        
        # Add grid properties
        self.part_obj.addProperty("App::PropertyInteger", "GridX", "Grid", "X grid position")
        self.part_obj.addProperty("App::PropertyInteger", "GridY", "Grid", "Y grid position")
        self.part_obj.addProperty("App::PropertyInteger", "GridZ", "Grid", "Z grid position")
        self.part_obj.GridX = x
        self.part_obj.GridY = y
        self.part_obj.GridZ = z
        
        # Create inner rod
        self._create_inner_rod(doc)
    
    def _create_outer_tube(self):
        """Create the outer tube geometry for the leg."""
        diagonal = self.leg.diagonal
        
        # Create hollow tube
        outer_radius = LEG_OUTER_DIAMETER / 2
        inner_radius = LEG_INNER_DIAMETER / 2 + 0.5
        
        outer_cyl = Part.makeCylinder(outer_radius, LEG_OUTER_LENGTH, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
        inner_hollow = Part.makeCylinder(inner_radius, LEG_OUTER_LENGTH, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
        tube = outer_cyl.cut(inner_hollow)
        
        # Rotate to align with diagonal
        z_axis = App.Vector(0, 0, 1)
        rot_axis = z_axis.cross(diagonal)
        
        if rot_axis.Length > 0.001:
            rot_axis.normalize()
            dot_product = max(-1.0, min(1.0, z_axis.dot(diagonal)))
            rot_angle = math.degrees(math.acos(dot_product))
            tube.rotate(App.Vector(0, 0, 0), rot_axis, rot_angle)
        elif diagonal.z < 0:
            tube.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 180)
        
        # Position tube
        tube.translate(self.leg.tube_start_local)
        
        return tube
    
    def _create_inner_rod(self, doc):
        """Create the inner rod with tip sphere."""
        diagonal = self.leg.diagonal
        
        # Create rod and sphere
        inner_rod = Part.makeCylinder(LEG_INNER_DIAMETER / 2, LEG_INNER_LENGTH,
                                      App.Vector(0, 0, 0), App.Vector(0, 0, 1))
        tip_sphere = Part.makeSphere(LEG_INNER_DIAMETER / 2, App.Vector(0, 0, LEG_INNER_LENGTH))
        rod_with_tip = inner_rod.fuse(tip_sphere)
        
        # Create object
        self.leg.inner_rod_obj = doc.addObject("Part::Feature", f"{self.name_prefix}_InnerRod_{self.position_code}")
        self.leg.inner_rod_obj.Shape = rod_with_tip
        self.leg.inner_rod_obj.ViewObject.ShapeColor = (1.0, 1.0, 0.0)
        self.part_obj.addObject(self.leg.inner_rod_obj)
        
        # Rotate and position rod
        z_axis = App.Vector(0, 0, 1)
        rot_axis = z_axis.cross(diagonal)
        
        if rot_axis.Length > 0.001:
            rot_axis.normalize()
            dot_product = max(-1.0, min(1.0, z_axis.dot(diagonal)))
            rot_angle = math.degrees(math.acos(dot_product))
            self.leg.inner_rod_obj.Placement.Rotation = App.Rotation(rot_axis, rot_angle)
        elif diagonal.z < 0:
            self.leg.inner_rod_obj.Placement.Rotation = App.Rotation(App.Vector(1, 0, 0), 180)
        
        self.leg.inner_rod_obj.Placement.Base = self.leg.rod_start_local


class RubiksCube:
    """Represents a complete Rubik's Cube with cubelets and legs."""
    
    def __init__(self, name="Cube"):
        """
        Initialize a Rubik's Cube.
        
        Args:
            name: Name for this cube instance
        """
        self.name = name
        self.model_obj = None  # FreeCAD App::Part container
        self.doc = None  # FreeCAD document
        self.corner_cubelets = {}  # Dict mapping (x,y,z) -> CornerCubelet
        self.edge_cubelets = {}    # Dict mapping (x,y,z) -> Part object
        self.center_cubelets = {}  # Dict mapping (x,y,z) -> Part object
        
        # Face definitions for rotations
        self.faces = {
            "R": {"axis": (1, 0, 0), "layer": lambda x, y, z: x == 1},
            "L": {"axis": (-1, 0, 0), "layer": lambda x, y, z: x == -1},
            "U": {"axis": (0, 1, 0), "layer": lambda x, y, z: y == 1},
            "D": {"axis": (0, -1, 0), "layer": lambda x, y, z: y == -1},
            "F": {"axis": (0, 0, 1), "layer": lambda x, y, z: z == 1},
            "B": {"axis": (0, 0, -1), "layer": lambda x, y, z: z == -1}
        }
    
    def create_geometry(self, doc):
        """
        Create all geometry for this cube.
        
        Args:
            doc: FreeCAD document
        """
        self.doc = doc
        
        # Create root container
        self.model_obj = doc.addObject("App::Part", self.name)
        
        # Create center pieces (6)
        center_positions = [
            (1, 0, 0, "R"), (-1, 0, 0, "L"),
            (0, 1, 0, "U"), (0, -1, 0, "D"),
            (0, 0, 1, "F"), (0, 0, -1, "B")
        ]
        
        for x, y, z, code in center_positions:
            shape = Part.makeBox(CUBELET_SIZE, CUBELET_SIZE, CUBELET_SIZE,
                                App.Vector(-CUBELET_SIZE/2, -CUBELET_SIZE/2, -CUBELET_SIZE/2))
            part = doc.addObject("App::Part", f"{self.name}_Center_{code}")
            geo = doc.addObject("Part::Feature", f"{self.name}_Center_{code}_Geo")
            geo.Shape = shape
            geo.ViewObject.ShapeColor = (0.7, 0.7, 0.7)
            part.addObject(geo)
            self.model_obj.addObject(part)
            part.Placement.Base = App.Vector(x * SPACING, y * SPACING, z * SPACING)
            
            part.addProperty("App::PropertyInteger", "GridX", "Grid", "X grid position")
            part.addProperty("App::PropertyInteger", "GridY", "Grid", "Y grid position")
            part.addProperty("App::PropertyInteger", "GridZ", "Grid", "Z grid position")
            part.GridX = x
            part.GridY = y
            part.GridZ = z
            
            self.center_cubelets[(x, y, z)] = part
        
        # Create edge pieces (12)
        edge_positions = [
            (1, 1, 0, "RU"), (1, -1, 0, "RD"), (1, 0, 1, "RF"), (1, 0, -1, "RB"),
            (-1, 1, 0, "LU"), (-1, -1, 0, "LD"), (-1, 0, 1, "LF"), (-1, 0, -1, "LB"),
            (0, 1, 1, "UF"), (0, 1, -1, "UB"), (0, -1, 1, "DF"), (0, -1, -1, "DB"),
        ]
        
        for x, y, z, code in edge_positions:
            shape = Part.makeBox(CUBELET_SIZE, CUBELET_SIZE, CUBELET_SIZE,
                                App.Vector(-CUBELET_SIZE/2, -CUBELET_SIZE/2, -CUBELET_SIZE/2))
            part = doc.addObject("App::Part", f"{self.name}_Edge_{code}")
            geo = doc.addObject("Part::Feature", f"{self.name}_Edge_{code}_Geo")
            geo.Shape = shape
            geo.ViewObject.ShapeColor = (0.6, 0.6, 0.6)
            part.addObject(geo)
            self.model_obj.addObject(part)
            part.Placement.Base = App.Vector(x * SPACING, y * SPACING, z * SPACING)
            
            part.addProperty("App::PropertyInteger", "GridX", "Grid", "X grid position")
            part.addProperty("App::PropertyInteger", "GridY", "Grid", "Y grid position")
            part.addProperty("App::PropertyInteger", "GridZ", "Grid", "Z grid position")
            part.GridX = x
            part.GridY = y
            part.GridZ = z
            
            self.edge_cubelets[(x, y, z)] = part
        
        # Create corner pieces with legs (8)
        corner_positions = [
            (1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1),
            (-1, 1, 1), (-1, 1, -1), (-1, -1, 1), (-1, -1, -1)
        ]
        
        for pos in corner_positions:
            corner = CornerCubelet(pos, self.name)
            corner.create_geometry(doc, self.model_obj)
            self.corner_cubelets[pos] = corner
    
    def get_corner(self, x, y, z):
        """Get corner cubelet at grid position."""
        return self.corner_cubelets.get((x, y, z))
    
    def get_leg_tip_position(self, corner_pos):
        """
        Get the world position of a leg tip.
        
        Args:
            corner_pos: (x, y, z) tuple for corner position
            
        Returns:
            App.Vector: World position of leg tip
        """
        corner = self.get_corner(*corner_pos)
        if corner:
            return corner.leg.get_tip_position_world()
        return None
    
    def set_leg_extension(self, corner_pos, extension_mm):
        """
        Set extension of a specific leg.
        
        Args:
            corner_pos: (x, y, z) tuple for corner position
            extension_mm: Extension amount in mm
        """
        corner = self.get_corner(*corner_pos)
        if corner:
            corner.leg.set_extension(extension_mm)
    
    def set_position(self, position):
        """Set the cube's position in world coordinates."""
        if self.model_obj:
            self.model_obj.Placement.Base = position
    
    def set_rotation(self, rotation):
        """Set the cube's rotation."""
        if self.model_obj:
            self.model_obj.Placement.Rotation = rotation
    
    def _get_face_cubelets(self, face_name):
        """Get all cubelet objects for a given face by checking their CURRENT world positions."""
        face_info = self.faces[face_name]
        axis_vector = App.Vector(*face_info["axis"])
        
        # Which coordinate to check based on axis
        if abs(axis_vector.x) > 0.5:
            coord_index = 0  # x
            target_value = axis_vector.x * SPACING
        elif abs(axis_vector.y) > 0.5:
            coord_index = 1  # y
            target_value = axis_vector.y * SPACING
        else:
            coord_index = 2  # z
            target_value = axis_vector.z * SPACING
        
        cubelets = []
        epsilon = 0.1  # Tolerance for position matching
        
        # Check ALL cubelets by their CURRENT world position
        all_cubelets = []
        for corner in self.corner_cubelets.values():
            all_cubelets.append(corner.part_obj)
        for edge in self.edge_cubelets.values():
            all_cubelets.append(edge)
        for center in self.center_cubelets.values():
            all_cubelets.append(center)
        
        for cubelet in all_cubelets:
            # Get current world position
            world_pos = cubelet.getGlobalPlacement().Base
            
            # Check if this cubelet is on the face
            if coord_index == 0:
                current_value = world_pos.x
            elif coord_index == 1:
                current_value = world_pos.y
            else:
                current_value = world_pos.z
            
            if abs(current_value - target_value) < epsilon:
                cubelets.append(cubelet)
        
        return cubelets
    
    def rotate_face(self, face_name, clockwise=True, steps=30, frame_delay=0.05):
        """
        Rotate a face of the cube.
        
        Args:
            face_name: Face to rotate ("R", "L", "U", "D", "F", "B")
            clockwise: Rotation direction
            steps: Number of animation steps
            frame_delay: Delay between frames in seconds
        """
        import time
        
        face_info = self.faces[face_name]
        axis = App.Vector(*face_info["axis"])
        
        # Get face cubelets
        face_cubelets = self._get_face_cubelets(face_name)
        
        if not face_cubelets:
            print(f"Warning: No cubelets found for face {face_name}")
            return
        
        # Create pivot
        pivot = self.doc.addObject("App::Part", f"Pivot_{face_name}")
        self.model_obj.addObject(pivot)
        
        # Move cubelets to pivot
        for cubelet in face_cubelets:
            self.model_obj.removeObject(cubelet)
            pivot.addObject(cubelet)
        
        # Center of rotation
        center = axis * SPACING
        
        # Animate rotation
        angle_per_step = (90.0 / steps) if clockwise else (-90.0 / steps)
        
        for step in range(steps):
            pivot.Placement.Rotation = App.Rotation(axis, angle_per_step * (step + 1))
            pivot.Placement.Base = center - pivot.Placement.Rotation.multVec(center)
            
            self.doc.recompute()
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
            self.model_obj.addObject(cubelet)
            
            # Set new placement
            cubelet.Placement = world_placement
            
            # NO NEED to update grid properties - we use world position for selection now!
        
        # Remove pivot
        self.model_obj.removeObject(pivot)
        self.doc.removeObject(pivot.Name)
        self.doc.recompute()
    
    def animate_leg_extension(self, corner_pos, target_extension, steps=30, frame_delay=0.05):
        """
        Animate a leg extension.
        
        Args:
            corner_pos: (x, y, z) tuple for corner position
            target_extension: Target extension in mm
            steps: Number of animation steps
            frame_delay: Delay between frames in seconds
        """
        import time
        
        corner = self.get_corner(*corner_pos)
        if not corner:
            print(f"Warning: Corner {corner_pos} not found")
            return
        
        start_extension = corner.leg.extension
        delta = (target_extension - start_extension) / steps
        
        for step in range(steps):
            new_extension = start_extension + delta * (step + 1)
            corner.leg.set_extension(new_extension)
            self.doc.recompute()
            App.Gui.updateGui()
            time.sleep(frame_delay)
        
        # Finalize
        corner.leg.set_extension(target_extension)
        self.doc.recompute()
    
    def rotate_face_with_leg_extensions(self, face_name, clockwise=True, leg_extensions=None, steps=30, frame_delay=0.05):
        """
        Rotate a face while simultaneously extending/retracting legs.
        
        Args:
            face_name: Face to rotate
            clockwise: Rotation direction
            leg_extensions: List of (corner_pos, target_extension) tuples
            steps: Number of animation steps
            frame_delay: Delay between frames in seconds
        """
        import time
        
        face_info = self.faces[face_name]
        axis = App.Vector(*face_info["axis"])
        layer_test = face_info["layer"]
        
        # Get face cubelets
        face_cubelets = self._get_face_cubelets(face_name)
        
        # Create pivot
        pivot = self.doc.addObject("App::Part", f"Pivot_{face_name}")
        self.model_obj.addObject(pivot)
        
        # Move cubelets to pivot
        for cubelet in face_cubelets:
            self.model_obj.removeObject(cubelet)
            pivot.addObject(cubelet)
        
        # Center of rotation
        center = axis * SPACING
        
        # Setup leg animations
        leg_anims = []
        if leg_extensions:
            for corner_pos, target_ext in leg_extensions:
                corner = self.get_corner(*corner_pos)
                if corner:
                    leg_anims.append({
                        'corner': corner,
                        'start': corner.leg.extension,
                        'target': target_ext,
                        'delta': (target_ext - corner.leg.extension) / steps
                    })
        
        # Animate
        angle_per_step = (90.0 / steps) if clockwise else (-90.0 / steps)
        
        for step in range(steps):
            # Rotate face
            pivot.Placement.Rotation = App.Rotation(axis, angle_per_step * (step + 1))
            pivot.Placement.Base = center - pivot.Placement.Rotation.multVec(center)
            
            # Update leg extensions (only for non-rotating corners)
            for leg_anim in leg_anims:
                new_ext = leg_anim['start'] + leg_anim['delta'] * (step + 1)
                leg_anim['corner'].leg.set_extension(new_ext)
            
            self.doc.recompute()
            App.Gui.updateGui()
            time.sleep(frame_delay)
        
        # Finalize rotation
        final_rotation = App.Rotation(axis, 90.0 if clockwise else -90.0)
        pivot.Placement.Rotation = final_rotation
        pivot.Placement.Base = center - pivot.Placement.Rotation.multVec(center)
        
        # Finalize leg extensions
        for leg_anim in leg_anims:
            leg_anim['corner'].leg.set_extension(leg_anim['target'])
        
        # Move cubelets back and update state
        for cubelet in face_cubelets:
            world_placement = cubelet.getGlobalPlacement()
            
            pivot.removeObject(cubelet)
            self.model_obj.addObject(cubelet)
            cubelet.Placement = world_placement
            
            # NO NEED to update grid properties - we use world position for selection now!
        
        # Remove pivot
        self.model_obj.removeObject(pivot)
        self.doc.removeObject(pivot.Name)
        self.doc.recompute()


def create_single_cube():
    """Create a single Rubik's Cube for testing."""
    doc_name = "SingleCube_OOP"
    
    # Clear Report View
    try:
        mw = App.Gui.getMainWindow()
        report_view = mw.findChild(mw.__class__, "Report view")
        if report_view:
            report_view.clear()
    except:
        pass
    
    # Close existing document
    if App.ActiveDocument and App.ActiveDocument.Name == doc_name:
        App.closeDocument(doc_name)
    
    doc = App.newDocument(doc_name)
    
    print("Creating Rubik's Cube (OOP)...")
    cube = RubiksCube("TestCube")
    cube.create_geometry(doc)
    
    doc.recompute()
    
    if hasattr(App, 'Gui'):
        App.Gui.SendMsgToActiveView("ViewFit")
    
    print(f"\nCube created successfully!")
    print(f"Centers: {len(cube.center_cubelets)}")
    print(f"Edges: {len(cube.edge_cubelets)}")
    print(f"Corners: {len(cube.corner_cubelets)}")
    
    return cube


if __name__ == "__main__":
    create_single_cube()
