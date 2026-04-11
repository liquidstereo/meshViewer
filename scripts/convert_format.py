import os
import argparse

import numpy as np
from alive_progress import alive_bar

from configs.defaults import MESH_DIR_ROOT, TARGET_ANIM_FPS
from configs.colorize import Msg

SUPPORTED_FORMATS = ('obj', 'ply')

def _collect_polymeshes(obj) -> list:
    from alembic.AbcGeom import IPolyMesh
    from alembic.Abc import kWrapExisting
    result = []
    for i in range(obj.getNumChildren()):
        child = obj.getChild(i)
        if IPolyMesh.matches(child.getMetaData()):
            result.append(IPolyMesh(child, kWrapExisting))
        else:
            result.extend(_collect_polymeshes(child))
    return result

def _triangulate(
    face_counts: np.ndarray,
    face_indices: np.ndarray,
) -> np.ndarray:
    faces = []
    offset = 0
    for n in face_counts:
        for tri in range(n - 2):
            faces.append([
                face_indices[offset],
                face_indices[offset + tri + 1],
                face_indices[offset + tri + 2],
            ])
        offset += int(n)
    if not faces:
        return np.empty((0, 3), dtype=np.int32)
    return np.array(faces, dtype=np.int32)

def _build_target_indices(
    time_sampling,
    n_orig: int,
    target_fps: float,
) -> np.ndarray:
    orig_times = np.array(
        [time_sampling.getSampleTime(i) for i in range(n_orig)],
        dtype=np.float64,
    )
    t_start = orig_times[0]
    t_end = orig_times[-1]
    target_times = np.arange(t_start, t_end + 1e-9, 1.0 / target_fps)
    indices = np.searchsorted(orig_times, target_times, side='right') - 1
    return np.clip(indices, 0, n_orig - 1).astype(np.int32)

def _sample_to_arrays(
    meshes: list,
    ss,
) -> tuple:
    all_verts, all_faces, all_uvs = [], [], []
    vert_offset = 0
    has_uv = True

    for m in meshes:
        schema = m.getSchema()
        samp = schema.getValue(ss)

        pts = np.array(samp.getPositions(), dtype=np.float32)
        fc = np.array(samp.getFaceCounts(), dtype=np.int32)
        fi = np.array(samp.getFaceIndices(), dtype=np.int32)
        faces = _triangulate(fc, fi) + vert_offset

        all_verts.append(pts)
        all_faces.append(faces)
        vert_offset += len(pts)

        if has_uv:
            uv_param = schema.getUVsParam()
            if uv_param.valid():
                try:
                    uv_samp = uv_param.getExpandedValue(ss)
                    all_uvs.append(
                        np.array(uv_samp.getVals(), dtype=np.float32)
                    )
                except Exception:
                    has_uv = False
            else:
                has_uv = False

    verts = np.vstack(all_verts)
    faces = (
        np.vstack(all_faces)
        if all_faces
        else np.empty((0, 3), dtype=np.int32)
    )
    uvs = np.vstack(all_uvs) if (has_uv and all_uvs) else None
    return verts, faces, uvs

def _write_obj(
    verts: np.ndarray,
    faces: np.ndarray,
    uvs: np.ndarray | None,
    out_path: str,
) -> None:
    with open(out_path, 'w') as f:
        for v in verts:
            f.write(f'v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n')
        if uvs is not None and len(uvs) == len(verts):
            for uv in uvs:
                f.write(f'vt {uv[0]:.6f} {uv[1]:.6f}\n')
            for face in faces:
                i0, i1, i2 = face[0] + 1, face[1] + 1, face[2] + 1
                f.write(f'f {i0}/{i0} {i1}/{i1} {i2}/{i2}\n')
        else:
            for face in faces:
                f.write(
                    f'f {face[0]+1} {face[1]+1} {face[2]+1}\n'
                )

def _write_ply(
    verts: np.ndarray,
    faces: np.ndarray,
    out_path: str,
) -> None:
    n_v, n_f = len(verts), len(faces)
    header = (
        'ply\n'
        'format binary_little_endian 1.0\n'
        f'element vertex {n_v}\n'
        'property float x\n'
        'property float y\n'
        'property float z\n'
        f'element face {n_f}\n'
        'property list uchar int vertex_indices\n'
        'end_header\n'
    )
    buf = np.empty(n_f, dtype=[('n', 'u1'), ('idx', '<i4', 3)])
    buf['n'] = 3
    buf['idx'] = faces.astype(np.int32)
    with open(out_path, 'wb') as f:
        f.write(header.encode('ascii'))
        f.write(verts.astype(np.float32).tobytes())
        f.write(buf.tobytes())

def _save_frame(
    verts: np.ndarray,
    faces: np.ndarray,
    uvs: np.ndarray | None,
    fmt: str,
    scene_name: str,
    idx: int,
    output_dir: str,
) -> str:
    out_path = os.path.join(
        output_dir, f'{scene_name}.{idx:04d}.{fmt}'
    )
    if fmt == 'obj':
        _write_obj(verts, faces, uvs, out_path)
    else:
        _write_ply(verts, faces, out_path)
    return out_path

def convert_abc(
    abc_path: str,
    output_dir_root: str = MESH_DIR_ROOT,
    fmt: str = 'obj',
    target_fps: float = TARGET_ANIM_FPS,
) -> None:
    from alembic.Abc import IArchive, ISampleSelector

    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(
            f'Unsupported format: {fmt!r}. '
            f'Choose from {SUPPORTED_FORMATS}'
        )
    if not os.path.isfile(abc_path):
        raise FileNotFoundError(f'File not found: {abc_path}')

    scene_name = os.path.splitext(
        os.path.basename(abc_path)
    )[0]
    output_dir = os.path.join(output_dir_root, scene_name)
    os.makedirs(output_dir, exist_ok=True)

    archive = IArchive(abc_path)
    meshes = _collect_polymeshes(archive.getTop())
    if not meshes:
        raise RuntimeError(
            'No PolyMesh geometry found in ABC file'
        )

    schema = meshes[0].getSchema()
    n_orig = schema.getNumSamples()
    target_indices = _build_target_indices(
        schema.getTimeSampling(), n_orig, target_fps
    )
    total = len(target_indices)

    with alive_bar(
        total,
        spinner=None,
        title='PLEASE WAIT…',
        title_length=19,
        length=20,
        dual_line=True,
        stats=True,
        elapsed=True,
    ) as bar:
        for out_idx, src_idx in enumerate(target_indices):
            ss = ISampleSelector(int(src_idx))
            verts, faces, uvs = _sample_to_arrays(meshes, ss)
            out_path = _save_frame(
                verts, faces, uvs,
                fmt, scene_name, out_idx, output_dir,
            )
            bar.title = 'PROCESSING…'
            bar.text = Msg.Dim(
                f'[{out_idx + 1:04d}/{total:04d}] {out_path}',
                end='',
            )
            bar()
        bar.title = 'DONE'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert Alembic to OBJ/PLY sequence'
    )
    parser.add_argument(
        'abc_path', type=str,
        help='Path to input .abc file',
    )
    parser.add_argument(
        '-o', '--output', type=str,
        default=MESH_DIR_ROOT,
        help=f'Output root directory (default: {MESH_DIR_ROOT})',
    )
    parser.add_argument(
        '-f', '--format', type=str,
        default='obj', choices=SUPPORTED_FORMATS,
        help='Output format: obj or ply (default: obj)',
    )
    parser.add_argument(
        '--fps', type=float,
        default=TARGET_ANIM_FPS,
        help=f'Resampling FPS (default: {TARGET_ANIM_FPS})',
    )
    args = parser.parse_args()
    convert_abc(args.abc_path, args.output, args.format, args.fps)
