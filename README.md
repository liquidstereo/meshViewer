# MeshViewer

An interactive 3D mesh viewer built on OpenGL with support for static meshes, frame sequences, point clouds, and real-time audio visualization.

---

## Updates

### Latest

- **Headless export** - `--headless` renders offscreen and exits once the
  save completes. Requires `-s`, rejects `-c`. Output is identical with and
  without it: render settings never change, only the capture path does.
  Fast asynchronous capture needs `RENDER_MSAA_SAMPLES = 0`; with MSAA on
  (default 8) both paths capture synchronously - slower, but anti-aliased.
- **Batch render** - pass several modes to `-m` as a comma separated list
  to play and save them one after another. Every mode starts from the
  same camera and frame index, and `SAVE_MODE_FILENAME` keeps the outputs
  in separate files. Works the same way with `--headless`.
- **NumPy playback** - `.npy` / `.npz` single files and sequences.
  `(N, 3)`, `(N, 6)` and `(H, W)` shapes are detected automatically;
  `DATA_NORMALIZE*` rescales skewed depth ranges.
- **Optional point normals** - `--no-normal` (or `CACHE_NORMALS`) shrinks
  the cache by roughly 20 percent when no normal-based mode is used.

---

## Overview

MeshViewer is a high-performance 3D mesh sequence viewer and real-time audio visualizer built on VTK (Visualization Toolkit). It supports 11+ mesh formats and 8+ audio formats and is optimized for seamless playback of both time-series mesh sequences and static models.

**Key Features**

- **High-speed sequence rendering:** A sliding-window frame buffer algorithm prevents OOM (Out of Memory) issues during large mesh sequence loading while maintaining high FPS.
- **Multiple visualization modes:**
  - **PBR & Texture:** Physically Based Rendering with HDRI IBL (Image-Based Lighting) for realistic material representation.
  - **Analysis modes:** Isoline, Normal Color, Mesh Quality, Edge Extract, and Vertex Label for precise data inspection.
  - **Point cloud:** Efficient visualization of large-scale point cloud data with custom shader injection and fog effect support.
- **Audio visualization (Waterfall):** Analyzes audio signals in real time and converts them into 3D waterfall geometry, enabling visual tracking of frequency and amplitude changes.
- **Capture optimization:** Asynchronous GPU readback via PBO (Pixel Buffer Object) allows per-frame screenshot saving without impacting playback performance.

**Supported Formats**

- **Mesh:** OBJ · PLY · STL · VTP · VTK · OFF · GLB · GLTF · DAE · 3DS · BYU · NPY · NPZ
- **Texture:** JPG · JPEG · PNG · BMP · TIF · TIFF · TGA
- **Audio:** WAV · MP3 · FLAC · OGG · AAC · M4A · AIF · AIFF

---

## Requirements

- [Python 3.10+](https://www.python.org/downloads/)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) (required — VTK must be installed via conda-forge, not pip)
- [ffmpeg](https://ffmpeg.org/download.html) — required for `mp4` / `mov`
  output only (`conda install -c conda-forge ffmpeg`). Without it, use
  `-f png`.
- **Linux is strongly recommended.** MeshViewer is built and tested on Linux only. Other platforms are untested.

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
python meshViewer.py -i <input> [-img <images>] [-s [<save>]] [-f <ext>] [-q <quality>] [-m <mode>] [-c] [-r <START-END>] [-v] [--no-cache] [--no-normal] [--preload-all] [--hide-info] [--headless]
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
# Play frames 100-400 only
python meshViewer.py -i character -r 100-400

# Record an h264 mp4 (default format, 'high' quality)
python meshViewer.py -i character -s

# Record a lossless mp4
python meshViewer.py -i character -s -q raw

# Save a PNG image sequence instead of a video
python meshViewer.py -i character -s -f png

# Accumulate captures across looped playback
python meshViewer.py -i character -s -c

# Export without opening a window; exits when the range is written
python meshViewer.py -i character -s -r 0-300 --headless
```

#### Other Options
```bash
# Start with all overlays hidden and enable debug logging
python meshViewer.py -i character --hide-info -v

# Start directly in a specific render mode
python meshViewer.py -i character -m isoline
python meshViewer.py -i pointcloud_seq -m point_white

# Batch render - one output per mode, in the given order
python meshViewer.py -i character -m 'mesh_quality, default, vtx' -s
python meshViewer.py -i character -m 'isoline, wire' -s --headless

# Build the cache without point normals (smaller cache)
python meshViewer.py -i character --no-normal
```

### Command-Line Arguments

| Arg | Long Form | Description | Default |
|-----|-----------|-------------|---------|
| `-i` | `--input` | **(required)** Mesh/audio directory name or file path | — |
| `-img` | `--images` | Image sequence overlay directory | `input/sequence/<name>` |
| `-s` | `--save` | Capture save path (omit value → `output/<name>` auto-set) | `None` |
| `-f` | `--format` | Output format: `mp4`, `mov`, `png`, `jpg` | `SAVE_EXT` (`mp4`) |
| `-q` | `--quality` | Video quality: `low`, `high`, `raw` (video only) | `SAVE_QUALITY` (`high`) |
| `-m` | `--mode` | Startup render mode, or a comma separated list to batch render | `STARTUP_MODE` |
| `-c` | `--continuous` | Accumulate capture index across loops (use with `-s`) | `False` |
| `-r` | `--range` | Playback frame range `START-END` (e.g. `0-500`) | `None` |
| `-v` | `--verbose` | Set log level to DEBUG | `False` |
| — | `--no-cache` | Skip NPZ/VTP cache; reload source files directly | `False` |
| — | `--no-normal` | Skip point normal generation (smaller cache; slower for normal-based modes) | `False` |
| — | `--preload-all` | Force full preload into RAM (OR-ed with `DEFAULT_PRELOAD_ALL`) | `False` |
| — | `--hide-info` | Hide all overlays on startup (`/` key to toggle) | `False` |
| — | `--headless` | Render offscreen and exit when saving finishes (requires `-s`, rejects `-c`) | `False` |

`-m` accepts, for meshes: `default`, `wire`, `smooth`, `isoline`,
`normal_color`, `mesh_quality`, `face_normal`, `depth`, `edge`, `vtx`,
`id`, `outline`, `pbr_tex.tex`, `pbr_tex.pbr`, `pbr_tex`; for point
clouds: `point_rgb`, `point_white`, `depth`. A mode that does not apply
to the loaded input is ignored with a warning.

Passing several modes as a comma separated list renders them one after
another in a single run, and `all` expands to every mode valid for the
loaded input type. Each mode starts from the same camera and frame
index, so the outputs stay comparable; with `-s`, `SAVE_MODE_FILENAME`
appends the mode name so the files do not overwrite each other. Batch
rendering works the same way under `--headless`.

```bash
python meshViewer.py -i mesh_dir -m wire,outline,id -s
python meshViewer.py -i mesh_dir -m all -s --headless
```

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
        └── pav_studio_03_4k.hdr   ← NOT included — download separately (see below)
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

> **This file is not included** in the repository due to its large file size (~80 MB).

**Download instructions:**

1. Visit **https://polyhaven.com/a/pav_studio_03**
2. Select resolution **4K** and format **HDR**
3. Download and place the file at `assets/hdri/pav_studio_03_4k.hdr`

If the file is missing, the viewer will still run — Smooth mode falls back to headlight illumination without IBL.

---

## Default Configuration

All defaults are defined in `configs/settings.py` and `configs/keybinding.py`.
Input-type-specific settings are in `configs/settings_mesh.py`,
`configs/settings_point_cloud.py`, `configs/settings_np_data.py`, and
`configs/settings_audio.py`.

The tables below are generated from the shipped settings files at build time.

**Window**

| Setting | Default |
|---|---|
| Width × Height | 1080 × 1080 |
| Aspect ratio | 1.0 |
| MSAA samples | 8 |
| FXAA | off |
| Monitor index | 0 |

**Playback**

| Setting | Default |
|---|---|
| Startup render mode | `default` |
| Startup ID style | `flat` |
| ID shading | `pbr` |
| Animation | on |
| Target FPS | 30 |
| Frame buffer size | RAM-dependent |
| Preload ahead | 87.5% of frame buffer size |
| Preload all | on |

**Scene**

| Setting | Default |
|---|---|
| Grid | off |
| Bounding box | off |
| Backface culling | off |
| Additional lighting | on |
| Turntable auto-rotation | off |
| Colorbar | on |
| HDRI IBL | on |

**Overlays**

Every overlay has its own master switch in `configs/settings_overlay.py`.
Setting one to `False` skips actor creation entirely, so the matching toggle
key stays inert.

| Setting | Overlay | Toggle key |
|---|---|---|
| `DISPLAY_STATUS` | Status text (top left) | `,` |
| `DISPLAY_SYSINFO` | CPU / MEM / GPU line and its sampler thread | — |
| `DISPLAY_MODE` | Mode and error messages | — |
| `DISPLAY_LOG` | Log overlay (bottom left) | `.` |
| `DISPLAY_COLORBAR` | Colormap legend | — |
| `DISPLAY_HELP` | Help overlay | `h` |
| `DISPLAY_SEQUENCE` | Image sequence overlay | `'` |
| `DISPLAY_AXES` | Orientation axes marker | — |
| `DISPLAY_CAM_DETAILS` | Camera detail lines in the status text | — |
| `DISPLAY_SEQ_ROUND` | Rounded corners on the sequence overlay | — |

Use `--hide-info` (or `SHOW_HIDE_INFO`) instead when the overlays should
merely start hidden and stay toggleable with `/`.

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
| `Ctrl+R` | Start / stop recording the current view |
| `Ctrl+C` | Quit from the terminal; shuts down the same way as `Escape` |

### Camera

| Key | Action |
|---|---|
| `r` / `KP_0` | Camera reset |
| `KP_5` | Center focal point on mesh |
| `c` | Parallel ↔ Perspective projection |
| `F1`–`F6` | Front / Back / Left / Right / Top / Bottom orthographic view |
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
| `4` | Smooth | Texture(albedo) → PBR.SHADER → PBR+TEX cycle, HDRI IBL |
| `s` | Smooth shading | Toggle smooth normal interpolation |
| `3` | Wireframe | Normal-based colormap over wire mesh |
| `5` | Isoline | Contour lines on selectable axis |
| `6` | Normal Color | Surface normal direction → RGB |
| `7` | Mesh Quality | Aspect ratio metric colormap (green = good) |
| `8` | Face Normal | Face normal glyph arrows |
| `9` | Depth | Camera-distance colormap |
| `0` | ID Color | Distinct color per connected mesh. `PgUp` / `PgDn` cycles ID (Flat) and ID (Shaded) |
| `1` | Outline | Silhouette outline in ID color. `b` shows the body again. Mesh only |
| `e` | Edge Extract | Feature angle-based edge lines |
| `2` | Vertex Label | Sparse vertex coordinate labels |
| `d` | Reduction | Mesh decimation (PBR lighting off) |

Both ID modes are mesh only; point cloud input rejects them. `ID (Flat)`
ignores lighting and paints a solid color per connected mesh, while
`ID (Shaded)` applies the shader named by `DEFAULT_ID_SHADER`. The style
the viewer starts in comes from `DEFAULT_ID_STYLE`.

### Scene & Overlays

| Key | Action |
|---|---|
| `F10` | Save screenshot |
| `` ` `` | Grid + BBox toggle |
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

Enabling FXAA and MSAA simultaneously causes conflicts on certain GPU drivers.
The defaults are already configured to avoid this (`RENDER_FXAA = False`,
`RENDER_MSAA_SAMPLES = 8`). If you changed these settings, restore the defaults
in `configs/settings.py`:

```python
RENDER_FXAA         = False   # do not enable while MSAA is active
RENDER_MSAA_SAMPLES = 8
```

To use FXAA instead of MSAA, disable MSAA first:

```python
RENDER_FXAA         = True
RENDER_MSAA_SAMPLES = 0
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

### Slow Mesh Sequence Preload

Automatic decimation runs per frame and dominates preload time on dense
sequences. It is skipped when the mesh is already close to the target
cell count.

In `configs/settings_mesh.py`:
```python
AUTO_DECIMATE_MIN_GAIN_RATIO = 0.5  # skip if n_faces <= MAX_CELLS * 1.5
CACHE_POINTS_FLOAT32 = True         # cache points as float32 (half size)
```

Raising `AUTO_DECIMATE_MIN_GAIN_RATIO` skips decimation for larger meshes
(faster load, higher GPU load). Changing `CACHE_POINTS_FLOAT32` requires
deleting `input/cache/` to take effect, since cache staleness is based on
file mtime.

### Some Frames Disappear or Flicker During Playback

Empty (0-byte) or truncated source files cannot be read by VTK. Such
frames are marked with `build_failed.marker` inside their cache directory
and are held at the nearest valid frame instead of rendering nothing.

Check the log for the affected frame count:
```
WARNING  Invalid frames held from nearest valid frame: N frames
```

Re-export the listed source files to restore them. To disable holding and
show empty frames instead, set `HOLD_INVALID_FRAME = False` in
`configs/settings_mesh.py`.

### Recorded File Size Varies Wildly Between Render Modes

This is expected. h264 is encoded at constant quality (CRF), so the bitrate
follows scene complexity rather than a fixed budget. `wire` and `edge` fill the
frame with thin high-contrast lines that defeat both spatial and temporal
prediction, while `depth` is a smooth gradient that compresses well - the same
sequence can differ by an order of magnitude.

The `high` default (`crf 16`, `yuv444p`) deliberately spends bits to keep thin
lines and overlay text sharp. For smaller files:

```bash
python meshViewer.py -i <name> -s -q low     # crf 28 + yuv420p
```

Or add an intermediate preset to `SAVE_QUALITY_PRESETS` in
`configs/settings.py`, or reduce `WINDOW_WIDTH` / `WINDOW_HEIGHT`.

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

### NPZ / NPY Depth Map Appears Flat

The Z distribution may be heavily skewed (e.g., most points near one depth extreme).
Enable log-scale normalization and per-axis scaling in `configs/settings_np_data.py`:

```python
DATA_NORMALIZE       = True        # enable normalization
DATA_NORMALIZE_LOG   = True        # log1p transform on Z before normalization
DATA_NORMALIZE_AXIS  = 'per_axis'  # normalize X, Y, Z axes independently
DATA_NORMALIZE_VALUE = 10.0        # target scale (adjust to taste)
```

Then rebuild the cache:

```bash
python meshViewer.py -i <name> --no-cache
```

### Audio Mode: Frame Seek

Use `←` / `→` keys to seek forward/backward by `AUDIO_SEEK_STEP` frames (default: 30).
Adjust the step size in `configs/settings_audio.py`:

```python
AUDIO_SEEK_STEP = 30
```

### Audio Mode: Flat Waveform in Silent Sections

Long silent sections may flatten the waveform. This is expected behavior — amplitude is
normalized globally via `global_max`. No action needed.

### High Memory Usage or OOM with Large Point Cloud Sequences

When loading large Gaussian Splat PLY sequences (1,000+ frames, 500k+ points per
frame), memory consumption may be significant.

The viewer automatically estimates required memory and switches from full preload to
sliding-window mode when loading would exceed ~70% of available RAM. No manual
intervention is required in most cases.

To force sliding-window mode explicitly:

In `configs/settings.py`:
```python
DEFAULT_PRELOAD_ALL = False
```

To reduce worker memory pressure further, lower the system resource ratio:

In `configs/settings.py`:
```python
DEFAULT_SYSTEM_USAGE = 0.50  # default: 0.80; recommended 0.50–0.60 on low-end systems
```

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
