"""Helper functions for plotting meshes through matplotlib."""

from typing import Literal, Union

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.axes import Axes


def create_figure(
    proj_type: Literal["persp", "ortho"] = "persp",
    fig_aspect: float = 1,
    headless: bool = False,
) -> tuple[Figure, Axes]:
    """Returns a figure/axis for 3d plotting."""
    if headless:
        fig = Figure(figsize=plt.figaspect(fig_aspect))
    else:
        fig = plt.figure(figsize=plt.figaspect(fig_aspect))
    ax = fig.add_subplot(111, projection="3d", computed_zorder=False)
    ax.set_proj_type(proj_type)
    return fig, ax


def create_split_figure(
    sync: bool = True, proj_type: Literal["persp", "ortho"] = "persp"
) -> tuple[Figure, Axes]:
    """Returns a figure composed of two axis for side-by-side 3d plotting.

    Params:
        sync: Whether or not to sync the two views once an interactive op
            has finished. Axis sharing like for 2d plots is not implemented
            for matplotlib 3d, so we simulate it with custom code.
        proj_type: Projection type

    Returns:
        fig: matplotlib figure
        axes: tuple of two axis
    """
    fig = plt.figure(figsize=plt.figaspect(0.5))
    ax0 = fig.add_subplot(
        1, 2, 1, projection="3d", proj_type=proj_type, computed_zorder=False
    )
    ax1 = fig.add_subplot(
        1, 2, 2, projection="3d", proj_type=proj_type, computed_zorder=False
    )

    sync_pending = False
    sync_dir = [None, None]

    def sync_views(a, b):
        b.view_init(elev=a.elev, azim=a.azim)
        b.set_xlim3d(a.get_xlim3d())
        b.set_ylim3d(a.get_ylim3d())
        b.set_zlim3d(a.get_zlim3d())

    def on_press(event):
        nonlocal sync_pending, sync_dir
        inaxes = event.inaxes in [ax0, ax1]
        if inaxes:
            sync_pending = True
            sync_dir = [ax0, ax1] if event.inaxes == ax0 else [ax1, ax0]

    def on_release(event):
        nonlocal sync_pending

        if sync_pending:
            sync_views(*sync_dir)
            sync_pending = False
            fig.canvas.draw_idle()

    if sync:
        fig.canvas.mpl_connect("button_press_event", on_press)
        fig.canvas.mpl_connect("button_release_event", on_release)

    return fig, (ax0, ax1)


def setup_axes(
    ax,
    min_corner: tuple[float, ...],
    max_corner: tuple[float, ...],
    azimuth: float = -139,
    elevation: float = 35,
    num_grid: int = 3,
):
    """Set axis view options.

    Params:
        ax: matplotlib axis
        min_corner: min data corner for computing zoom values
        max_corner: max data corner for computing zoom values
        azimuth: camera view angle in degrees
        elevation: camera view angle in degrees
        num_grid: the number of grid lines. Set to zero to disable grid.
    """

    ax.set_xlim(min_corner[0], max_corner[0])
    ax.set_ylim(min_corner[1], max_corner[1])
    ax.set_zlim(min_corner[2], max_corner[2])
    if num_grid > 0:
        ax.xaxis.set_major_locator(MaxNLocator(num_grid))
        ax.yaxis.set_major_locator(MaxNLocator(num_grid))
        ax.zaxis.set_major_locator(MaxNLocator(num_grid))
    else:
        ax.grid(False)
        ax.set_axis_off()
    ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.set_box_aspect(
        (
            max_corner[0] - min_corner[0],
            max_corner[1] - min_corner[1],
            max_corner[2] - min_corner[2],
        )
    )
    ax.view_init(elev=elevation, azim=azimuth)
    # https://github.com/matplotlib/matplotlib/blob/v3.5.0/lib/mpl_toolkits/mplot3d/axes3d.py#L1460-L1499


def plot_mesh(
    ax,
    verts: np.ndarray,
    faces: np.ndarray,
    face_normals: np.ndarray = None,
    vertex_normals: np.ndarray = None,
    **kwargs,
):
    """Add a mesh to the axis.

    Params:
        ax: matplotlib axis
        verts: (N,3) array of vertices
        faces: (M,F) array of faces with F=3 for triangles and F=4 for quads
        face_normals: (M,3) array of face normals (optional). When supplied, additional
            arrows will be plotted to indicate the normal per face.
        vertex_normals: (N,3) array of vertex normals (optional). When supplied,
            additional arrows will be plotted to indicate the normal per vertex.
        kwargs: additional arguments passed to Poly3DCollection
    """
    # Better colors? https://matplotlib.org/stable/gallery/mplot3d/voxels_rgb.html
    # https://stackoverflow.com/questions/56864378/how-to-light-and-shade-a-poly3dcollection
    kwargs = {"linewidth": 0.2, "zorder": 1, **kwargs}
    mesh = Poly3DCollection(verts[faces], **kwargs)
    mesh.set_edgecolor("w")
    ax.add_collection3d(mesh)

    if face_normals is not None:
        centers = verts[faces].mean(1)
        plot_normals(ax, centers, face_normals, color="purple")

    if vertex_normals is not None:
        plot_normals(ax, verts, vertex_normals, color="lime")


def plot_samples(ax, xyz: np.ndarray, sdf_values: np.ndarray = None):
    """Plots sampling points and colorizes them based on sdf classification."""
    colors = np.zeros_like(xyz)
    if sdf_values is not None:
        colors[sdf_values <= 0] = (1.0, 1.0, 0.0)
    ax.scatter(
        xyz[..., 0], xyz[..., 1], xyz[..., 2], s=2, c=colors.reshape(-1, 3), alpha=0.5
    )


def plot_normals(ax, origins: np.ndarray, dirs: np.ndarray, **kwargs):
    """Plots normals from points and directions"""
    kwargs = {"linewidth": 0.5, "zorder": 2, "length": 0.1, **kwargs}

    ax.quiver(
        origins[:, 0],
        origins[:, 1],
        origins[:, 2],
        dirs[:, 0],
        dirs[:, 1],
        dirs[:, 2],
        **kwargs,
    )


def plot_edges(ax, src, dst, **kwargs):
    """Plots pair of points as edges"""
    lines = np.stack((src, dst), 1)
    art = Line3DCollection(lines, **kwargs)
    ax.add_collection3d(art)


def create_mesh_figure(
    verts: np.ndarray,
    faces: np.ndarray,
    face_normals: np.ndarray = None,
    vertex_normals: np.ndarray = None,
    fig_kwargs: dict = None,
    plotMesh:bool = True,
) -> tuple[Figure, Axes]:
    """Helper to quickly plot a single mesh.

    This method creates a 3d enabled figure, adds the given mesh to the plot
    and estimates the view limit from mesh bounds.

    Params:
        verts: (N,3) array of vertices
        faces: (M,F) array of faces with F=3 for triangles and F=4 for quads
        face_normals: (M,3) array of face normals (optional). When supplied, additional
            arrows will be plotted to indicate the normal per face.
        vertex_normals: (N,3) array of vertex normals (optional). When supplied,
            additional arrows will be plotted to indicate the normal per vertex.
        fig_kwargs: additional arguments passed to create_figure

    Returns:
        fig: matplotlib figure
        ax: matplotlib axis
    """
    min_corner = verts.min(0)
    max_corner = verts.max(0)
    mask = abs(max_corner - min_corner) < 1e-5
    min_corner[mask] -= 0.5
    max_corner[mask] += 0.5

    fig_kwargs = fig_kwargs or {}

    fig, ax = create_figure(**fig_kwargs)
    if plotMesh:
        plot_mesh(ax, verts, faces, face_normals, vertex_normals)
    setup_axes(ax, min_corner, max_corner)
    return fig, ax


def generate_rotation_gif(
    filename: str,
    fig: Figure,
    axs: Union[Axes, list[Axes]],
    azimuth_range: tuple[float, float] = (0, 2 * np.pi),
    num_images: int = 64,
    total_time: float = 5.0,
):
    """Generates a rotating figure and stores it as animated GIF.

    Params:
        filename: path to resulting file
        fig: matplotlib figure
        ax: matplotlib 3d axis or list of axis
        azimuth_range: the incremental range of the rotation. Animation
            starts at ax.azimuth + azimut_range[0]
        num_images: total number of frames
        total_time: total animation time in seconds
    """
    import imageio

    azimuth_incs = np.degrees(
        np.linspace(azimuth_range[0], azimuth_range[1], num_images, endpoint=False)
    )

    if isinstance(axs, Axes):
        axs = [Axes]

    azimuth0, elevation0 = zip(*[(ax.azim, ax.elev) for ax in axs])

    with imageio.get_writer(
        filename, mode="I", duration=total_time / num_images
    ) as writer:
        canvas = FigureCanvasAgg(fig)
        for ainc in azimuth_incs:
            for ax, az0, el0 in zip(axs, azimuth0, elevation0):
                ax.view_init(elev=el0, azim=az0 + ainc)
            canvas.draw()
            buf = canvas.buffer_rgba()
            img = np.asarray(buf)
            writer.append_data(img)
