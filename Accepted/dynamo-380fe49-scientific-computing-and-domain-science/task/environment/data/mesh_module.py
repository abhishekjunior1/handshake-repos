"""
mesh_module.py
==============
1D mesh generation for finite difference / finite volume heat conduction solver.

Generates a uniform mesh on [x_left, x_right] with N cells.
Provides node (cell-center) coordinates, face coordinates, element connectivity,
cell widths, and face areas for a rod/bar of specified cross-sectional area.
"""

import numpy as np


class Mesh1D:
    """
    Uniform 1D mesh for finite difference/volume discretization.

    Attributes
    ----------
    n_cells : int
        Number of computational cells.
    n_faces : int
        Number of internal faces (n_cells - 1) plus 2 boundary faces = n_cells + 1.
    x_left : float
        Left boundary coordinate [m].
    x_right : float
        Right boundary coordinate [m].
    length : float
        Domain length [m].
    dx : float
        Uniform cell width [m].
    cross_section_area : float
        Cross-sectional area of the rod [m^2].
    node_coords : np.ndarray
        Cell-center coordinates, shape (n_cells,).
    face_coords : np.ndarray
        Face coordinates, shape (n_cells + 1,).
    cell_widths : np.ndarray
        Width of each cell, shape (n_cells,). Uniform = dx for all.
    face_areas : np.ndarray
        Area of each face, shape (n_cells + 1,). Uniform = cross_section_area.
    connectivity : np.ndarray
        Element connectivity: connectivity[i] = [left_face_index, right_face_index]
        for cell i, shape (n_cells, 2).
    """

    def __init__(self, n_cells, x_left, x_right, cross_section_area):
        """
        Create a uniform 1D mesh.

        Parameters
        ----------
        n_cells : int
            Number of cells (must be >= 2).
        x_left : float
            Left boundary position [m].
        x_right : float
            Right boundary position [m].
        cross_section_area : float
            Cross-sectional area of the rod/bar [m^2].
        """
        if n_cells < 2:
            raise ValueError("n_cells must be at least 2")
        if x_right <= x_left:
            raise ValueError("x_right must be greater than x_left")
        if cross_section_area <= 0:
            raise ValueError("cross_section_area must be positive")

        self.n_cells = n_cells
        self.n_faces = n_cells + 1
        self.x_left = x_left
        self.x_right = x_right
        self.length = x_right - x_left
        self.dx = self.length / n_cells
        self.cross_section_area = cross_section_area

        # Face coordinates (cell boundaries)
        self.face_coords = np.linspace(x_left, x_right, n_cells + 1)

        # Node coordinates (cell centers)
        self.node_coords = 0.5 * (self.face_coords[:-1] + self.face_coords[1:])

        # Cell widths (uniform)
        self.cell_widths = np.full(n_cells, self.dx)

        # Face areas (uniform cross-section)
        self.face_areas = np.full(self.n_faces, cross_section_area)

        # Connectivity: cell i is bounded by face i (left) and face i+1 (right)
        self.connectivity = np.column_stack([
            np.arange(n_cells),
            np.arange(1, n_cells + 1)
        ])

    def get_face_distances(self):
        """
        Compute distances between adjacent cell centers.

        Returns
        -------
        np.ndarray
            Distance between cell centers across each internal face,
            shape (n_cells - 1,). For uniform mesh, all values equal dx.
        """
        return np.diff(self.node_coords)

    def get_cell_volumes(self):
        """
        Compute cell volumes (width * cross-sectional area).

        Returns
        -------
        np.ndarray
            Volume of each cell [m^3], shape (n_cells,).
        """
        return self.cell_widths * self.cross_section_area

    def __repr__(self):
        return (f"Mesh1D(n_cells={self.n_cells}, "
                f"domain=[{self.x_left}, {self.x_right}], "
                f"dx={self.dx:.6e})")
