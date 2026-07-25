"""
boundary_conditions.py
======================
Boundary condition specification and application for 1D heat conduction solver.

Supports:
- Dirichlet (fixed temperature)
- Neumann (prescribed heat flux)
- Robin (convection: h*(T - T_inf))
- Radiation (Stefan-Boltzmann: eps*sigma*(T^4 - T_env^4), linearized)

Handles left and right boundaries of the 1D domain independently.
"""

import numpy as np


def create_dirichlet_bc(temperature):
    """
    Create a Dirichlet (fixed temperature) boundary condition.

    Parameters
    ----------
    temperature : float
        Fixed boundary temperature [K].

    Returns
    -------
    dict
        Boundary condition specification with 'type' and 'value'.
    """
    return {
        'type': 'dirichlet',
        'value': temperature
    }


def create_neumann_bc(heat_flux):
    """
    Create a Neumann (prescribed heat flux) boundary condition.

    Convention: positive heat_flux means heat flowing INTO the domain.

    Parameters
    ----------
    heat_flux : float
        Heat flux at the boundary [W/m^2].
        Positive = heat entering the domain.

    Returns
    -------
    dict
        Boundary condition specification.
    """
    return {
        'type': 'neumann',
        'value': heat_flux
    }


def create_robin_bc(h_conv, T_ambient, area):
    """
    Create a Robin (convection) boundary condition.

    The convective flux is: q = h_conv * (T_ambient - T_boundary) * area
    This is converted to an equivalent Neumann flux using the current
    boundary temperature, or handled as a linearized source.

    Parameters
    ----------
    h_conv : float
        Convective heat transfer coefficient [W/(m^2·K)].
    T_ambient : float
        Ambient temperature [K].
    area : float
        Boundary face area [m^2].

    Returns
    -------
    dict
        Robin BC specification with convection parameters.
    """
    return {
        'type': 'robin',
        'h_conv': h_conv,
        'T_ambient': T_ambient,
        'area': area
    }


def create_radiation_bc(emissivity, T_environment, stefan_boltzmann, area):
    """
    Create a radiation boundary condition.

    Parameters
    ----------
    emissivity : float
        Surface emissivity at the boundary.
    T_environment : float
        Environment temperature for radiation exchange [K].
    stefan_boltzmann : float
        Stefan-Boltzmann constant [W/(m^2·K^4)].
    area : float
        Boundary face area [m^2].

    Returns
    -------
    dict
        Radiation BC specification.
    """
    return {
        'type': 'radiation',
        'emissivity': emissivity,
        'T_environment': T_environment,
        'stefan_boltzmann': stefan_boltzmann,
        'area': area
    }


def apply_robin_as_neumann(robin_bc, T_boundary):
    """
    Convert a Robin BC to an equivalent Neumann BC using current temperature.

    Parameters
    ----------
    robin_bc : dict
        Robin boundary condition from create_robin_bc().
    T_boundary : float
        Current temperature at the boundary cell [K].

    Returns
    -------
    dict
        Equivalent Neumann BC with computed heat flux.
    """
    h = robin_bc['h_conv']
    T_inf = robin_bc['T_ambient']
    area = robin_bc['area']
    # Heat flux into domain: h * (T_ambient - T_boundary) * area
    flux = h * (T_inf - T_boundary) * area
    return create_neumann_bc(flux)


def apply_radiation_as_neumann(radiation_bc, T_boundary):
    """
    Convert a radiation BC to an equivalent Neumann BC using current temperature.

    Uses linearized radiation for implicit treatment.

    Parameters
    ----------
    radiation_bc : dict
        Radiation BC from create_radiation_bc().
    T_boundary : float
        Current temperature at the boundary cell [K].

    Returns
    -------
    dict
        Equivalent Neumann BC with computed radiative flux.
    """
    eps = radiation_bc['emissivity']
    T_env = radiation_bc['T_environment']
    sigma = radiation_bc['stefan_boltzmann']
    area = radiation_bc['area']
    # Net radiation INTO the domain (environment to surface)
    flux = eps * sigma * (T_env**4 - T_boundary**4) * area
    return create_neumann_bc(flux)


def resolve_boundary_condition(bc_spec, T_boundary):
    """
    Resolve any boundary condition type into a form usable by the solver.

    Dirichlet and Neumann pass through unchanged. Robin and radiation
    are linearized to equivalent Neumann conditions.

    Parameters
    ----------
    bc_spec : dict
        Boundary condition specification from any create_*_bc function.
    T_boundary : float
        Current temperature at the boundary cell [K].

    Returns
    -------
    dict
        Resolved BC with 'type' ('dirichlet' or 'neumann') and 'value'.
    """
    bc_type = bc_spec['type']

    if bc_type == 'dirichlet':
        return bc_spec
    elif bc_type == 'neumann':
        return bc_spec
    elif bc_type == 'robin':
        return apply_robin_as_neumann(bc_spec, T_boundary)
    elif bc_type == 'radiation':
        return apply_radiation_as_neumann(bc_spec, T_boundary)
    else:
        raise ValueError(f"Unknown boundary condition type: {bc_type}")
