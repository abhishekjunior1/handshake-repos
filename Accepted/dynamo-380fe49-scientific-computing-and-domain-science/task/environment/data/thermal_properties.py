"""
thermal_properties.py
=====================
Material thermal properties for 1D transient heat transfer simulation.

Provides temperature-dependent thermal conductivity k(T), specific heat cp(T),
density, and emissivity. Properties are interpolated from tabulated data
representative of a steel alloy (e.g., AISI 304 stainless steel).

Functions for computing face conductivities (harmonic and arithmetic means)
are also provided for use at cell interfaces in finite difference/volume schemes.
"""

import numpy as np


# ============================================================================
# Tabulated material property data
# Temperature points [K] for property interpolation
# ============================================================================

# Reference temperatures for interpolation tables [K]
_T_TABLE = np.array([300.0, 400.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0,
                     1100.0, 1200.0, 1300.0, 1400.0, 1500.0])

# Thermal conductivity [W/(m·K)] - increases slightly with temperature for steel
_K_TABLE = np.array([14.9, 16.6, 18.3, 19.8, 21.3, 22.6, 23.9, 25.1,
                     26.2, 27.3, 28.3, 29.2, 30.1])

# Specific heat capacity [J/(kg·K)] - increases with temperature
_CP_TABLE = np.array([477.0, 515.0, 540.0, 557.0, 574.0, 586.0, 598.0, 611.0,
                      624.0, 636.0, 648.0, 659.0, 670.0])

# Reference density [kg/m^3] - assumed constant (mild temperature dependence neglected)
DENSITY = 7900.0

# Surface emissivity (oxidized stainless steel)
EMISSIVITY = 0.85


def get_thermal_conductivity(temperature):
    """
    Compute thermal conductivity at given temperature(s) via linear interpolation.

    Parameters
    ----------
    temperature : float or np.ndarray
        Temperature [K]. Values outside the table range are clamped
        (extrapolation uses boundary values).

    Returns
    -------
    float or np.ndarray
        Thermal conductivity [W/(m·K)].
    """
    return np.interp(temperature, _T_TABLE, _K_TABLE)


def get_specific_heat(temperature):
    """
    Compute specific heat capacity at given temperature(s) via linear interpolation.

    Parameters
    ----------
    temperature : float or np.ndarray
        Temperature [K]. Values outside the table range are clamped.

    Returns
    -------
    float or np.ndarray
        Specific heat capacity [J/(kg·K)].
    """
    return np.interp(temperature, _T_TABLE, _CP_TABLE)


def get_density():
    """
    Return material density (constant, temperature-independent).

    Returns
    -------
    float
        Density [kg/m^3].
    """
    return DENSITY


def get_emissivity():
    """
    Return surface emissivity for radiation calculations.

    Returns
    -------
    float
        Emissivity (dimensionless, 0 < eps <= 1).
    """
    return EMISSIVITY


def compute_harmonic_mean(k_left, k_right):
    """
    Compute the harmonic mean of two conductivity values.

    The harmonic mean is appropriate for computing effective conductivity
    at a cell interface when the cells have different conductivities
    (analogous to resistances in series).

    Parameters
    ----------
    k_left : float or np.ndarray
        Conductivity of the left cell [W/(m·K)].
    k_right : float or np.ndarray
        Conductivity of the right cell [W/(m·K)].

    Returns
    -------
    float or np.ndarray
        Harmonic mean conductivity [W/(m·K)].
        Returns 2 * k_left * k_right / (k_left + k_right).
    """
    return 2.0 * k_left * k_right / (k_left + k_right)


def compute_arithmetic_mean(k_left, k_right):
    """
    Compute the arithmetic mean of two conductivity values.

    Simple average, sometimes used for face conductivity when
    cells are of equal size and properties vary smoothly.

    Parameters
    ----------
    k_left : float or np.ndarray
        Conductivity of the left cell [W/(m·K)].
    k_right : float or np.ndarray
        Conductivity of the right cell [W/(m·K)].

    Returns
    -------
    float or np.ndarray
        Arithmetic mean conductivity [W/(m·K)].
        Returns (k_left + k_right) / 2.
    """
    return (k_left + k_right) / 2.0


def get_all_properties(temperature):
    """
    Convenience function to retrieve all thermal properties at once.

    Parameters
    ----------
    temperature : float or np.ndarray
        Temperature [K].

    Returns
    -------
    dict
        Dictionary with keys 'conductivity', 'specific_heat', 'density',
        'emissivity' and their respective values.
    """
    return {
        'conductivity': get_thermal_conductivity(temperature),
        'specific_heat': get_specific_heat(temperature),
        'density': get_density(),
        'emissivity': get_emissivity(),
    }
