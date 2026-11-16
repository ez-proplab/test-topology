# Topology Optimization for CAD Models

A Python executable application for performing **SIMP-based topology optimization** on arbitrary CAD geometries. The tool automatically handles mesh voxelization, hollowness enforcement, and structural optimization with real-time 3D visualization.

## Features

- **Arbitrary Geometry Support**: Import STL, OBJ, PLY, OFF, and other CAD formats
- **Automatic Hollowness**: Ensures sufficient interior void for structural optimization
- **SIMP Algorithm**: Industry-standard Solid Isotropic Material with Penalization method
- **3D Visualization**: Real-time pyvista-based viewport with density coloring
- **Multiple BC Types**: Cantilever, bridge, 3-point bending, and custom boundary conditions
- **Export Results**: Save optimized geometry as STL or OBJ
- **Cross-Platform**: Builds to standalone executables on Windows, macOS, and Linux

## Installation

### From Source

```bash
# Clone or download the project
cd python_app

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Build Executable

```bash
# Build standalone executable
python build_executable.py

# The executable will be in the dist/ folder
# Windows: dist/TopologyOptimizer.exe
# macOS: dist/TopologyOptimizer
# Linux: dist/TopologyOptimizer
```

## Usage

### GUI Mode

```bash
python main.py
```

1. **Load Geometry**: Click "Load CAD Model" to import an STL/OBJ file, or use "Test Geometry" for built-in examples
2. **Configure Parameters**: Set volume fraction, penalization, filter radius, etc.
3. **Voxelize**: Click "Voxelize Geometry" to convert the mesh to a voxel grid
4. **Optimize**: Click "Run Optimization" to start the SIMP algorithm
5. **Export**: Save the result as STL

### Command-Line Mode

```bash
# Optimize a CAD file
python main.py --cli --input model.stl --volfrac 0.4 --penal 3.0

# Use test geometry
python main.py --cli --test beam --bc-type cantilever --max-iter 50

# Full options
python main.py --cli \
    --input part.stl \
    --output result.stl \
    --volfrac 0.3 \
    --penal 3.0 \
    --filter-radius 2.5 \
    --max-iter 80 \
    --resolution 40 \
    --wall-thickness 2 \
    --hollow-fraction 0.6 \
    --threshold 0.5 \
    --bc-type cantilever
```

### Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--input, -i` | None | Input CAD file (STL, OBJ, etc.) |
| `--output, -o` | optimized_result.stl | Output file path |
| `--test` | beam | Test geometry: beam, l_bracket, plate, cylinder |
| `--volfrac` | 0.4 | Volume fraction constraint (0.1-0.9) |
| `--penal` | 3.0 | SIMP penalization power |
| `--filter-radius` | 2.0 | Sensitivity filter radius (voxels) |
| `--max-iter` | 50 | Maximum iterations |
| `--resolution` | 30 | Voxel resolution (along longest axis) |
| `--wall-thickness` | 2 | Minimum wall thickness (voxels) |
| `--hollow-fraction` | 0.6 | Interior hollow fraction (0-1) |
| `--threshold` | 0.5 | Density threshold for export |
| `--bc-type` | cantilever | Boundary condition type |

## Algorithm

### SIMP Method

The **Solid Isotropic Material with Penalization** method interpolates material stiffness:

```
E(x) = x^p × E₀
```

where:
- `x` = relative density (0 = void, 1 = solid)
- `p` = penalization power (typically 3)
- `E₀` = Young's modulus of solid material

### Hollowness Enforcement

The tool ensures the input geometry has sufficient interior void for optimization:

1. **Voxelize** the input mesh into a 3D grid
2. **Identify surface voxels** (adjacent to empty space) — these form the fixed outer shell
3. **Erode interior** to create design space — the optimizer can add/remove material here
4. **Preserve minimum wall thickness** to maintain structural integrity

This guarantees the optimizer has room to redistribute material while keeping the outer shape recognizable.

### Optimization Loop

```
for each iteration:
    1. Assemble stiffness matrix K (SIMP interpolation)
    2. Solve Ku = F (Conjugate Gradient solver)
    3. Compute sensitivities dc/dx
    4. Apply sensitivity filter (prevent checkerboarding)
    5. Update densities (Optimality Criteria method)
    6. Check convergence
```

## Architecture

```
python_app/
├── main.py                    # Entry point (GUI + CLI)
├── requirements.txt           # Dependencies
├── build_executable.py        # PyInstaller build script
├── README.md                  # This file
└── src/
    ├── core/
    │   ├── mesh_utils.py      # Mesh loading, voxelization, hollowness
    │   ├── fea.py             # Finite element analysis (hex8 elements)
    │   └── optimizer.py       # SIMP topology optimization
    ├── gui/
    │   └── main_window.py     # PyQt5 GUI with pyvista viewport
    └── utils/
        └── exporters.py       # STL/OBJ export utilities
```

## Dependencies

- **numpy** - Numerical computing
- **scipy** - Sparse matrices, CG solver, image processing
- **trimesh** - Mesh loading, voxelization, boolean operations
- **PyQt5** - GUI framework
- **pyvista** - 3D visualization (VTK-based)
- **pyvistaqt** - PyQt5 integration for pyvista
- **pyinstaller** - Executable building

## Troubleshooting

### Build Issues

```bash
# If pyvistaqt is not found:
pip install pyvistaqt

# If VTK issues:
pip install vtk --upgrade

# If trimesh boolean operations fail:
pip install manifold3d
```

### Performance Tips

- Lower voxel resolution (20-30) for quick iterations
- Use fewer max iterations (20-30) for initial exploration
- Increase penalization (p=4-5) for sharper solid/void results
- Larger filter radius = smoother results but larger features

### Memory Issues

For large meshes, the FEA solver may require significant memory:
- Reduce resolution to 20-25 voxels
- Use `--resolution 20` in CLI mode
- Each voxel adds 24 DOFs to the system

## License

MIT License

## References

- Sigmund, O. (2001). "A 99 line topology optimization code written in Matlab"
- Bendsøe, M.P. & Sigmund, O. (2003). "Topology Optimization: Theory, Methods and Applications"
