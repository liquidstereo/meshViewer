# MeshViewer

A PyVista/VTK-based interactive 3D mesh viewer built on OpenGL, supporting static meshes, frame sequences, point clouds, and real-time audio visualization.

---

## Overview

- **Supported mesh formats:** OBJ · PLY · STL · VTP · VTK · OFF · GLB · GLTF · DAE · 3DS · BYU
- **Supported texture formats:** JPG · JPEG · PNG · BMP · TIF · TIFF · TGA
- **Supported audio formats:** WAV · MP3 · FLAC · OGG · AAC · M4A · AIF · AIFF

---

## Requirements

- **Python** 3.10+
- **Miniconda** (required — VTK must be installed via conda-forge, not pip)

---

## Usage

### Installation

#### Prerequisites
- [Python 3.10+](https://www.python.org/downloads/)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)

#### Setup Instructions

1. **Clone the Repository**
    ```bash
    git clone https://github.com/liquidstereo/meshViewer.git && cd meshViewer
    ```

2. **Create Conda Environment**
    ```bash
    conda create -n meshViewer python=3.10
    conda activate meshViewer
    ```

3. **Install VTK via conda-forge** *(required — do NOT use `pip install vtk`)*
    ```bash
    conda install -c conda-forge vtk
    ```

4. **Install Remaining Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

### Command Line Interface

Execute the script from the project root directory using the following syntax:

```bash
python meshViewer.py -i <input> [-img <images>] [-s [<save>]] [-c] [-r <START-END>] [-v] [--no-cache] [--hide-info]
```

### Usage Examples

#### Mesh Sequence
```bash
# Load all mesh files from input/mesh/character/
python meshViewer.py -i character
```

#### Single File
```bash
# Load a single OBJ file by relative path
python meshViewer.py -i input/mesh/model.obj
```

#### Audio Visualization
```bash
# Activate audio visualization mode with a WAV file
python meshViewer.py -i input/audio/track.wav
```

#### Frame Range & Capture
```bash
# Play frames 100–400 only
python meshViewer.py -i character -r 100-400

# Save screenshots continuously during looped playback
python meshViewer.py -i character -s -c
```

#### Other Options
```bash
# Start with all overlays hidden and enable debug logging
python meshViewer.py -i character --hide-info -v
```

### Command-Line Arguments

| Arg | Long Form | Description | Default |
|-----|-----------|-------------|---------|
| `-i` | `--input` | **(required)** Mesh/audio directory name or file path | — |
| `-img` | `--images` | Image sequence overlay directory | `input/sequence/<name>` |
| `-s` | `--save` | Screenshot save path (omit value → `output/<name>/` auto-set) | `None` |
| `-c` | `--continuous` | Accumulate screenshot index across loops (use with `-s`) | `False` |
| `-r` | `--range` | Playback frame range `START-END` (e.g. `0-500`) | `None` |
| `-v` | `--verbose` | Set log level to DEBUG | `False` |
| — | `--no-cache` | Skip NPZ/VTP cache; reload source files directly | `False` |
| — | `--hide-info` | Hide all overlays on startup (`/` key to toggle) | `False` |

## Input Directory Structure

Place your files under the following directories before running:

```
meshViewer/
├── input/
│   ├── mesh/               ← mesh sequences and single mesh files
│   │   └── <name>/         ← directory: python meshViewer.py -i <name>
│   │       ├── frame_0001.obj
│   │       ├── frame_0002.obj
│   │       └── ...
│   ├── sequence/           ← image sequence overlay (optional)
│   │   └── <name>/
│   │       ├── frame_0001.png
│   │       └── ...
│   ├── texture/            ← texture files for mesh (optional)
│   │   ├── <name>/         ← subdirectory: <name>/<name>.jpg
│   │   │   └── <name>.jpg
│   │   └── <name>.jpg      ← root-level: searched when single file is loaded
│   └── audio/              ← audio files for audio visualization mode
│       └── track.wav
└── assets/
    └── hdri/
        └── pav_studio_03_4k.hdr   ← ⚠️ NOT included — download separately (see below)
```

Texture lookup is performed automatically when a mesh is loaded:
it searches `input/texture/<stem>/` and `input/texture/<stem>.*` in that order.
If both exist simultaneously, an error is raised.

### HDRI Environment Map

The **Smooth mode** (`4` key) uses PBR (Physically Based Rendering) with HDRI image-based lighting (IBL).
This requires an `.hdr` file placed at:

```
assets/hdri/pav_studio_03_4k.hdr
```

> ⚠️ **This file is not included** in the repository due to its large file size (~80 MB).

**Download instructions:**

1. Visit **https://polyhaven.com/a/pav_studio_03**
2. Select resolution **4K** and format **HDR**
3. Download and place the file at `assets/hdri/pav_studio_03_4k.hdr`

If the file is missing, the viewer will still run — Smooth mode falls back to headlight illumination without IBL.

---

## Default Configuration

All defaults are defined in `configs/defaults.py` and `configs/keybinding.py`.

**Window**

| Setting | Default |
|---|---|
| Width × Height | 1024 × 1024 |
| Aspect ratio | 1.0 (square) |
| MSAA samples | 8 |
| FXAA | enabled |
| Monitor index | 0 |

**Playback**

| Setting | Default |
|---|---|
| Startup render mode | `pbr_tex` |
| Animation | enabled |
| Target FPS | 30 |
| Frame buffer size | 1500 frames |
| Preload ahead | 600 frames |
| Preload all | enabled |

**Scene**

| Setting | Default |
|---|---|
| Grid | on |
| Bounding box | on |
| Backface culling | on |
| Additional lighting | off |
| Turntable auto-rotation | on |
| Colorbar | on |

---

## Key Bindings

### Playback

| Key | Action |
|---|---|
| `Space` | Play / Pause |
| `←` / `→` | Step backward / forward one frame |
| `↑` / `↓` | Jump to first / last frame |
| `BackSpace` | Full reset (mode, camera, state) |
| `Escape` | Quit |

### Camera

| Key | Action |
|---|---|
| `r` / `KP_0` | Camera reset |
| `KP_5` | Center focal point on mesh |
| `c` | Parallel ↔ Perspective projection |
| `F1` / `F2` / `F3` / `F4` | Front / Back / Top / Side view |
| `KP_7` / `KP_9` | Zoom in / out |
| `KP_1` / `KP_3` | Dolly in / out |
| `KP_4` / `KP_6` | Rotate around Y axis |
| `KP_2` / `KP_8` | Rotate around X axis |
| `Ctrl+KP_4/6` | Truck left / right |
| `Ctrl+KP_2/8` | Pedestal down / up |
| `KP_.` | Auto-turntable toggle |

### Render Modes

| Key | Mode | Description |
|---|---|---|
| `q` | Default | Flat shading with headlight |
| `4` | Smooth | PBR+Texture → Texture → PBR cycle, HDRI IBL |
| `s` | Smooth shading | Toggle smooth normal interpolation |
| `3` | Wireframe | Normal-based colormap over wire mesh |
| `5` | Isoline | Contour lines on selectable axis |
| `6` | Normal Color | Surface normal direction → RGB |
| `7` | Mesh Quality | Scaled Jacobian metric colormap |
| `8` | Face Normal | Face normal glyph arrows |
| `9` | Depth | Camera-distance colormap |
| `e` | Edge Extract | Feature angle-based edge lines |
| `2` | Vertex Label | Sparse vertex coordinate labels |
| `d` | Reduction | Mesh decimation (PBR lighting off) |

### Scene & Overlays

| Key | Action |
|---|---|
| `` ` `` | Save screenshot |
| `1` | Grid + BBox toggle |
| `b` | Backface culling / mesh occluder toggle |
| `Tab` | Cycle actor visibility |
| `PgUp` / `PgDn` | Axis cycle (CAM → Z → Y → X) |
| `KP_+` / `KP_-` | Mode parameter increment / decrement |
| `/` | Toggle all overlays |
| `h` | Help overlay |

---

## Notes

- **VTK must be installed via conda-forge.**
  `pip install vtk` installs `vtkOSOpenGLRenderWindow` (headless renderer) which cannot
  display a window. Always use `conda install -c conda-forge vtk`.
- **Audio mode** requires `librosa` and `soundfile`. The audio file can be placed in
  `input/audio/` or specified as a direct path.
- **Cache files** (VTP/NPZ) are written to `input/cache/` on first load to speed up
  subsequent runs. Use `--no-cache` to bypass.

---

## License

This project is licensed under the MIT License.
