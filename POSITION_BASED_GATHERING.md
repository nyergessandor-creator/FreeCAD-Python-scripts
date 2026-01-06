"""
Position-Based Cubelet Gathering Test

This demonstrates the key difference between the old (broken) and new (correct) approach:

OLD APPROACH (Wrong):
- Used static name-based mapping
- After rotation, cubelets moved but were still gathered by their original names
- Result: Wrong cubelets selected, collisions

NEW APPROACH (Correct):
- Checks actual current position in 3D space
- After rotation, cubelets are gathered based on where they actually are
- Result: Correct cubelets selected, just like a real Rubik's cube

Example:
--------
Initial state:
  Corner_RUF is at position (25, 25, 25)
  
After rotating R face 90°:
  Corner_RUF is now at position (25, -25, 25)  <- moved!
  
OLD: Would still select Corner_RUF for R face (WRONG - it's not on R face anymore!)
NEW: Checks position and finds cubelets currently at x=25 (CORRECT!)

This is exactly how the three.js simulation works:

```javascript
for (const cubelet of this.cubelets) {
    const pos = cubelet.position.clone();
    let val;
    if (axisIdx === 0) val = pos.x;
    else if (axisIdx === 1) val = pos.y;
    else val = pos.z;
    
    if (Math.abs(val - slice) < epsilon) {
        this.activeCubelets.push(cubelet);
    }
}
```

Key functions in our implementation:

1. get_cubelets_at_position(cube_objects, axis_index, slice_value)
   - Iterates through ALL cubelets
   - Checks each cubelet's Shape.CenterOfMass
   - Gathers cubelets where position matches slice_value on the specified axis
   
2. get_legs_at_position(cube_objects, axis_index, slice_value)
   - Same approach for leg segments
   - Legs follow their cubelets dynamically

3. animate_face_rotation(face, cube_objects, ...)
   - Maps face letter to (axis_index, slice_value, axis_vector)
   - Calls position-based gathering functions
   - Rotates whatever is currently at that position
"""
