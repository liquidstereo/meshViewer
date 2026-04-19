# MeshViewer

A PyVista/VTK-based interactive 3D mesh viewer built on OpenGL, supporting static meshes, frame sequences, point clouds, and real-time audio visualization.

---

## Overview

MeshViewer is a high-performance 3D mesh sequence viewer and real-time audio visualization tool built on PyVista and VTK (Visualization Toolkit). It supports 11+ mesh formats and 8+ audio formats, and is optimized for seamless playback of time-series frame data as well as static models.

**Key Features**

- **High-speed sequence rendering:** A sliding-window frame buffer algorithm prevents OOM (Out of Memory) issues during large mesh sequence loading while maintaining high FPS.
- **Multiple visualization modes:**
  - **PBR & Texture:** Physically Based Rendering with HDRI IBL (Image-Based Lighting) for realistic material representation.
  - **Analysis modes:** Isoline, Normal Color, Mesh Quality, Edge Extract, and Vertex Label for precise data inspection.
  - **Point cloud:** Efficient visualization of large-scale point cloud data with custom shader injection and fog effect support.
- **Audio visualization (Waterfall):** Analyzes audio signals in real time and converts them into 3D waterfall geometry, enabling visual tracking of frequency and amplitude changes.
- **Capture optimization:** Asynchronous GPU readback via PBO (Pixel Buffer Object) allows per-frame screenshot saving without impacting playback performance.

**Supported Formats**

- **Mesh:** OBJ · PLY · STL · VTP · VTK · OFF · GLB · GLTF · DAE · 3DS · BYU
- **Texture:** JPG · JPEG · PNG · BMP · TIF · TIFF · TGA
- **Audio:** WAV · MP3 · FLAC · OGG · AAC · M4A · AIF · AIFF

---

## Requirements

- [Python 3.10+](https://www.python.org/downloads/)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) (required — VTK must be installed via conda-forge, not pip)

---

## Usage

### Installation

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

- All defaults are defined in `configs/settings.py` and `configs/keybinding.py`.
- For more details, refer to the comments in `configs/settings*.py`.

**Window**

| Setting | Default |
|---|---|
| Width × Height | 1024 × 1024 |
| Aspect ratio | 1.0 (square) |
| MSAA samples | 0 (disabled) |
| FXAA | enabled |
| Monitor index | 0 |

**Playback**

| Setting | Default |
|---|---|
| Startup render mode | `default` |
| Animation | enabled |
| Target FPS | 30 |
| Frame buffer size | 1500 frames |
| Preload ahead | 1800 frames |
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
| HDRI IBL | enabled |

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
| `F1`–`F6` | Front / Back / Left / Right / Top / Bottom view |
| `Tab` | Mesh axis swap cycle (OFF → Y↔Z → X↔Z → X↔Y) |
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
| `;` | Grid only toggle |
| `b` | Backface culling / mesh occluder toggle |
| `F11` | Theme toggle (black ↔ white) |
| `F12` | Cycle actor visibility |
| `PgUp` / `PgDn` | Axis cycle (CAM → Z → Y → X) |
| `KP_+` / `KP_-` | Mode parameter increment / decrement |
| `/` | Toggle all overlays |
| `.` | Log overlay show/hide |
| `,` | Status text show/hide |
| `'` | Image sequence overlay show/hide |
| `h` | Help overlay |

---

## Troubleshooting

### Black Screen or Flickering

Caused by an FXAA/MSAA conflict on certain GPU drivers.

In `configs/settings.py`:
```python
RENDER_FXAA         = False
RENDER_MSAA_SAMPLES = 8
```

### Slow Initial Load

The PBR/Smooth mode preloads a large HDRI file (~80 MB) at startup.
To disable HDRI loading (falls back to headlight illumination):

In `configs/settings_mesh.py`:
```python
HDRI_ENABLE = False
```

### High CPU Usage or Slow Sequence Load

Reduce the worker thread count by lowering the system usage ratio.

In `configs/settings.py`:
```python
DEFAULT_SYSTEM_USAGE = 0.50  # default: 0.80; recommended 0.50-0.60 on low-end CPUs
```

### Cache Corruption or Stale Mesh Data

If mesh data appears incorrect after re-exporting source files, bypass the cache:

```bash
python meshViewer.py -i <name> --no-cache
```

To permanently clear the cache, delete the `input/cache/` directory.

### Texture Not Displayed

- Place the texture at `input/texture/<stem>/` or `input/texture/<stem>.*`
- The texture filename stem must match the mesh filename stem exactly
- If both a subdirectory and a root-level file exist for the same stem, an error is
  raised — remove one

### Audio Mode: Frame Seek

Use `←` / `→` keys to seek forward/backward by `AUDIO_SEEK_STEP` frames (default: 30).
Adjust the step size in `configs/settings_audio.py`:

```python
AUDIO_SEEK_STEP = 30
```

### Audio Mode: Flat Waveform in Silent Sections

Long silent sections may flatten the waveform. This is expected behavior — amplitude is
normalized globally via `global_max`. No action needed.

---

## Notes

- **VTK must be installed via conda-forge.**
  `pip install vtk` installs `vtkOSOpenGLRenderWindow` (headless renderer) which cannot
  display a window. Always use `conda install -c conda-forge vtk`.
- **Audio mode** requires `librosa` and `soundfile`. The audio file can be placed in
  `input/audio/` or specified as a direct path.
- **Cache files** (VTP/NPZ) are written to `input/cache/` on first load to speed up
  subsequent runs. Use `--no-cache` to bypass.
- **Point cloud files** (PLY/other with no face data) are auto-detected on load and
  start in `point_rgb` mode (vertex color display). Use the `2` key to toggle.

---

## License

This project is licensed under the MIT License.
