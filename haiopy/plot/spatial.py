"""
Plot for spatially distributed data.
"""
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import numpy as np
import copy

from haiopy.coordinates import Coordinates


def scatter(coordinates, projection='3d', ax=None, set_ax=True, **kwargs):
    """Plot the x, y, and z coordinates as a point cloud in three-dimensional
    space.

    Parameters
    ----------
    coordinates : Coordinates
        Coordinates object with respective positions.
    projection : '3d', 'ortho'
        Projection to be used for the plot. Only three-dimensional projections
        are supported.
    ax : matplotlib.axis (optional)
        If no axis is defined, a new axis in a new figure is created.
    set_ax: boolean
        Set the limits of the axis according to the points in coordinates. The
        default is True.
    **kwargs :
        Additional key value arguments are passed to matplotlib.pyplot.scatter.

    Returns
    ax : matplotlib.axes
        The axis used for the plot.

    """
    if not isinstance(coordinates, Coordinates):
        raise ValueError("The coordinates need to be a Coordinates object")

    # copy to avoid changing the coordinate system of the original object
    xyz = copy.deepcopy(coordinates).get_cart()

    ax = _setup_axes(
        projection, ax, set_ax, bounds=(np.min(xyz), np.max(xyz)), **kwargs)

    # plot
    ax.scatter(
        xyz[..., 0],
        xyz[..., 1],
        xyz[..., 2], **kwargs)

    # labeling
    ax.set_xlabel('X [m]')
    ax.set_ylabel('Y [m]')
    ax.set_zlabel('Z [m]')

    return ax


def quiver(
        origins, endpoints, projection='3d', ax=None, set_ax=True, **kwargs):
    """Plot vectors from their origins (x, y, z) to their endpoints (u, v, w).

    Parameters
    ----------
    origins : Coordinates
        The origins of the vectors.
    endpoints : Coordinates
        The endpoints of the vectors.
    projection : '3d', 'ortho'
        Projection to be used for the plot. Only three-dimensional projections
        are supported.
    ax : matplotlib.axis (optional)
        If no axis is defined, a new axis in a new figure is created.
    set_ax: boolean
        Set the limits of the axis according to the points in coordinates. The
        default is True.
    **kwargs :
        Additional key value arguments are passed to matplotlib.pyplot.scatter.

    Returns
    ax : matplotlib.axes
        The axis used for the plot.

    """
    if not (
            isinstance(origins, Coordinates)
            and isinstance(endpoints, Coordinates)):
        raise ValueError(
            "The origins and endpoints need to be Coordinates objects")

    # copy to avoid changing the coordinate system of the original object
    xyz = copy.deepcopy(origins).get_cart()
    uvw = copy.deepcopy(endpoints).get_cart()

    min_val = min(np.min(xyz), np.min(uvw))
    max_val = max(np.max(xyz), np.max(uvw))
    ax = _setup_axes(
        projection, ax, set_ax, bounds=(min_val, max_val), **kwargs)

    color = kwargs.get('color', None)

    # plot
    ax.quiver(*xyz.T, *uvw.T, color=color)

    return ax


def _setup_axes(projection=Axes3D.name, ax=None,
                set_ax=True, bounds=(-1, 1), **kwargs):
    """Setup axes' limits and labels for 3D-plots.

    Parameters
    ----------
    projection : '3d', 'ortho'
        Projection to be used for the plot. Only three-dimensional projections
        are supported.
    ax : matplotlib.axis (optional)
        If no axis is defined, a new axis in a new figure is created.
    set_ax: boolean
        Set the limits of the axis according to the points in coordinates. The
        default is True.
    bounds: tuple (min, max)
        The lower and upper boundaries of the data to be plotted. This is used
        for the axes' limits.
    **kwargs :
        Additional key value arguments are passed to matplotlib.pyplot.scatter.

    Returns
    ax : matplotlib.axes
        The axis used for the plot.

    """
    if ax is None:
        # create equal aspect figure for distortion free display
        # (workaround for ax.set_aspect('equal', 'box'), which is currently not
        #  working for 3D axes.)
        plt.figure(figsize=plt.figaspect(1.))
        ax = plt.gca(projection=projection)

    if 'Axes3D' not in ax.__str__():
        raise ValueError("Only three-dimensional axes supported.")

    # add defaults to kwargs
    kwargs['marker'] = kwargs.get('marker', '.')
    kwargs['c'] = kwargs.get('k', '.')

    # labeling
    ax.set_xlabel('X [m]')
    ax.set_ylabel('Y [m]')
    ax.set_zlabel('Z [m]')

    # equal axis limits for distortion free  display
    if set_ax:
        # unfortunately ax.set_aspect('equal') does not work on Axes3D
        ax_lims = (bounds[0]-.15*np.abs(bounds[0]),
                   bounds[1]+.15*np.abs(bounds[1]))

        ax.set_xlim(ax_lims)
        ax.set_ylim(ax_lims)
        ax.set_zlim(ax_lims)

    return ax
