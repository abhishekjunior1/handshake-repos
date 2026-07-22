"""
heat_source.py
==============
Heat source and sink terms for 1D transient heat transfer simulation.

Provides functions for:
- Internal volumetric heat generation (e.g., Joule heating, nuclear decay)
- Radiation exchange with surroundings (Stefan-Boltzmann law)
- Linearized radiation coefficient for implicit schemes
- Convective heat loss to ambient environment
"""

import numpy as np


# Stefan-Boltzmann constant [W/(m^2·K^4)]
STEFAN_BOLTZMANN_CONSTANT = 5.670374419e-8


def compute_volumetric_heat_source(x_coords, q_dot_max, x_center, width):
    """
    Compute a Gaussian-distributed volumetric heat source.

    Models localized internal heating (e.g., laser absorption, induction heating)
    as a Gaussian profile centered at x_center.

    Parameters
    ----------
    x_coords : np.ndarray
        Spatial coordinates of cell centers [m].
    q_dot_max : float
        Peak volumetric heat generation rate [W/m^3].
    x_center : float
        Center of the heat source [m].
    width : float
        Characteristic width (standard deviation) of the Gaussian [m].

    Returns
    -------
    np.ndarray
        Volumetric heat source at each cell center [W/m^3].
    """
    return q_dot_max * np.exp(-((x_coords - x_center) ** 2) / (2.0 * width ** 2))


def compute_uniform_heat_source(n_cells, q_dot):
    """
    Compute a spatially uniform volumetric heat source.

    Parameters
    ----------
    n_cells : int
        Number of cells in the mesh.
    q_dot : float
        Uniform volumetric heat generation rate [W/m^3].

    Returns
    -------
    np.ndarray
        Constant heat source array [W/m^3], shape (n_cells,).
    """
    return np.full(n_cells, q_dot)


def compute_radiation_loss(T_surface, T_environment, emissivity, stefan_boltzmann):
    """
    Compute radiative heat loss from a surface via Stefan-Boltzmann law.

    The net radiative heat flux from the surface is:
        q_rad = emissivity * stefan_boltzmann * (T_surface^4 - T_environment^4)

    Positive value means heat leaving the surface (loss).

    Parameters
    ----------
    T_surface : float or np.ndarray
        Surface temperature [K].
    T_environment : float or np.ndarray
        Environment (surroundings) temperature [K].
    emissivity : float
        Surface emissivity (0 < emissivity <= 1).
    stefan_boltzmann : float
        Stefan-Boltzmann constant [W/(m^2·K^4)].

    Returns
    -------
    float or np.ndarray
        Net radiative heat flux [W/m^2]. Positive = heat loss from surface.
    """
    return emissivity * stefan_boltzmann * (T_surface**4 - T_environment**4)


def compute_linearized_radiation_coefficient(T_surface, T_environment, emissivity, stefan_boltzmann):
    """
    Compute the linearized radiation heat transfer coefficient.

    This is the derivative of the radiation flux with respect to surface
    temperature, used for Newton linearization in implicit solvers:
        h_rad = emissivity * sigma * (T_s^2 + T_env^2) * (T_s + T_env)

    This allows radiation to be treated similarly to convection:
        q_rad ≈ h_rad * (T_surface - T_environment)

    Parameters
    ----------
    T_surface : float or np.ndarray
        Surface temperature [K].
    T_environment : float or np.ndarray
        Environment temperature [K].
    emissivity : float
        Surface emissivity (0 < emissivity <= 1).
    stefan_boltzmann : float
        Stefan-Boltzmann constant [W/(m^2·K^4)].

    Returns
    -------
    float or np.ndarray
        Linearized radiation coefficient [W/(m^2·K)].
    """
    return (emissivity * stefan_boltzmann *
            (T_surface**2 + T_environment**2) * (T_surface + T_environment))


def compute_convection_loss(T_surface, T_ambient, h_conv):
    """
    Compute convective heat loss from a surface.

    Uses Newton's law of cooling:
        q_conv = h_conv * (T_surface - T_ambient)

    Parameters
    ----------
    T_surface : float or np.ndarray
        Surface temperature [K].
    T_ambient : float or np.ndarray
        Ambient fluid temperature [K].
    h_conv : float
        Convective heat transfer coefficient [W/(m^2·K)].

    Returns
    -------
    float or np.ndarray
        Convective heat flux [W/m^2]. Positive = heat loss from surface.
    """
    return h_conv * (T_surface - T_ambient)


def compute_total_surface_loss(T_surface, T_environment, T_ambient,
                               emissivity, stefan_boltzmann, h_conv):
    """
    Compute combined radiative + convective heat loss from a surface.

    Parameters
    ----------
    T_surface : float or np.ndarray
        Surface temperature [K].
    T_environment : float
        Radiation environment temperature [K].
    T_ambient : float
        Convection ambient temperature [K].
    emissivity : float
        Surface emissivity.
    stefan_boltzmann : float
        Stefan-Boltzmann constant [W/(m^2·K^4)].
    h_conv : float
        Convective heat transfer coefficient [W/(m^2·K)].

    Returns
    -------
    float or np.ndarray
        Total surface heat flux [W/m^2].
    """
    q_rad = compute_radiation_loss(T_surface, T_environment, emissivity, stefan_boltzmann)
    q_conv = compute_convection_loss(T_surface, T_ambient, h_conv)
    return q_rad + q_conv
