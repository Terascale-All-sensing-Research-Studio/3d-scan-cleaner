import argparse
import logging

import trimesh
import numpy as np
import pymeshfix as mf
import pyransac3d as pyrsc


def rotation_matrix_from_vectors(vec1, vec2):
    a, b = (vec1 / np.linalg.norm(vec1)).reshape(3), (
        vec2 / np.linalg.norm(vec2)
    ).reshape(3)
    v = np.cross(a, b)
    if any(v):  # if not all zeros then
        c = np.dot(a, b)
        s = np.linalg.norm(v)
        kmat = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        return np.eye(3) + kmat + kmat.dot(kmat) * ((1 - c) / (s ** 2))

    else:
        return np.eye(3)  # cross of all zeros only occurs on identical directions


def normalize_mesh(mesh):
    # Get the overall size of the object
    mesh_min, mesh_max = np.min(mesh.vertices, axis=0), np.max(mesh.vertices, axis=0)
    size = mesh_max - mesh_min

    # Center the object
    translation = ((size / 2.0) + mesh_min)
    mesh.vertices -= translation

    # Normalize scale of the object
    scale = (1.0 / np.max(size))
    mesh.vertices *= (1.0 / np.max(size))

    return mesh, translation, scale


def discard_extraneous(mesh, bbx):
    # Shrink bounding box
    for p_, n_ in zip(
        [
            [bbx, 0, 0],
            [-bbx, 0, 0],
            [0, bbx, 0],
            [0, -bbx, 0],
            [0, 0, bbx],
            [0, 0, -bbx],
        ],
        [
            [-1, 0, 0],
            [1, 0, 0],
            [0, -1, 0],
            [0, 1, 0],
            [0, 0, -1],
            [0, 0, 1],
        ],
    ):
        mesh = trimesh.intersections.slice_mesh_plane(mesh, n_, p_)
    return mesh


def remove_plane(
    mesh, 
    ransac_threshold=0.01, 
    plane_offset=0.005, 
    trim_amount=0.6,
    fix_winding=True,
    reorient=True,
    normalize=True,
    keep_largest=True,
    close_holes=True,
    verbose=False,
):
    if verbose:
        print("Cleaning mesh with {} vertices, {} faces".format(mesh.vertices.shape[0], mesh.faces.shape[0]))
        print("Reorient:            {}".format(reorient))
        print("Normalize:           {}".format(normalize))
        print("Keep All Components: {}".format(not keep_largest))
        print("Close Holes:         {}".format(close_holes))
        print("Fix Winding:         {}".format(fix_winding))
    
    if fix_winding:
        trimesh.repair.fix_winding(mesh)
    orig_num_pts = mesh.vertices.shape[0]

    # Normalize the mesh to unit cube
    mesh, trans, scale = normalize_mesh(mesh)
    
    # Fit plane to mesh
    if verbose:
        print("Fitting plane using ransac")
    best_eq, _ = pyrsc.Plane().fit(mesh.vertices, ransac_threshold)

    # Convert to point normal form
    n = best_eq[:3]
    n = n / np.dot(n, n)
    p = [0, 0, -float(best_eq[3] / best_eq[2])]

    # Do initial slice
    if verbose:
        print("Removing plane")
    new_mesh = trimesh.intersections.slice_mesh_plane(mesh, n, p)

    # Re-orient normal vector
    if new_mesh.vertices.shape[0] < (orig_num_pts * 0.5):
        n = -n

    # Get upright transformation
    rot_m = rotation_matrix_from_vectors(np.array([0, 1, 0]), np.array(n))

    # Edge plane up a little and cut
    p_cur = p + (n * plane_offset)
    new_mesh = trimesh.intersections.slice_mesh_plane(mesh, n, p_cur)

    # The object will be centered, so discard the surrounding environment
    if verbose:
        print("Discarding extraneous geometry")
    new_mesh = discard_extraneous(new_mesh, (trim_amount/2))

    # Retain only the largest connected component
    if keep_largest:
        new_mesh = new_mesh.split(only_watertight=False)
        new_mesh = new_mesh[np.argmax([m.vertices.shape[0] for m in new_mesh])]

    # Orient the mesh upright
    if reorient:
        new_mesh.vertices = np.dot(new_mesh.vertices, rot_m)

    # Undo normalization
    if not normalize:
        new_mesh.vertices *= (1/scale)
        new_mesh.vertices += trans

    # Close mesh holes
    if close_holes:
        if verbose:
            print("Filling mesh holes")
        meshfix = mf.MeshFix(new_mesh.vertices, new_mesh.faces)
        meshfix.repair(verbose=verbose)
        new_mesh = trimesh.Trimesh(vertices=meshfix.v, faces=meshfix.f)

    return new_mesh


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(dest="input", type=str, help="Path to the input file.")
    parser.add_argument(dest="output", type=str, help="Path to the output file.")
    parser.add_argument(
        "--normalize",
        default=False,
        action="store_true",
        help="If passed, will scale and translate the mesh to the center of a "
        + "unit cube.",
    )
    parser.add_argument(
        "--no_reorient",
        default=False,
        action="store_true",
        help="If passed, will not reorient the mesh according to the ground plane.",
    )
    parser.add_argument(
        "--no_close_holes",
        default=False,
        action="store_true",
        help="If passed will not attempt to fill holes in the cleaned model.",
    )
    parser.add_argument(
        "--no_fix_winding",
        default=False,
        action="store_true",
        help="If passed will not fix the winding of the input mesh.",
    )
    parser.add_argument(
        "--keep_all",
        default=False,
        action="store_true",
        help="If passed, keep all connected components after removing extraneous"
        + "geometry. Else will only keep the largest connected component.",
    )
    parser.add_argument(
        "--verbose",
        default=False,
        action="store_true",
        help="Print out more detailed status information.",
    )
    parser.add_argument(
        "--ransac_threshold",
        type=float,
        default=0.01,
        help="Threshold distance from the plane which is considered inlier.",
    )
    parser.add_argument(
        "--plane_offset",
        type=float,
        default=0.005,
        help="Distance to offset the plane before discarding points below the"
        + "plane.",
    )
    parser.add_argument(
        "--trim",
        type=float,
        default=0.6,
        help="Size of the unit cube used to discard extraneous geometry. This "
        + "will work even if the normalize flag is not passed.",
    )
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    mesh = trimesh.load(args.input)
    remove_plane(
        mesh=mesh,
        ransac_threshold=args.ransac_threshold, 
        plane_offset=args.plane_offset, 
        trim_amount=args.trim,
        normalize=args.normalize,
        fix_winding=(not args.no_fix_winding),
        reorient=(not args.no_reorient),
        keep_largest=(not args.keep_all),
        close_holes=(not args.no_close_holes),
        verbose=args.verbose,
    ).export(args.output)