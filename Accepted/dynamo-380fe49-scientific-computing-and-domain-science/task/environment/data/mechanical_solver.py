"""
mechanical_solver.py
====================
Thermal-mechanical solver for 1D rod/bar problems.

Computes thermal strain, thermal stress (for constrained bars), and
displacement (for free expansion). Handles temperature-dependent
Young's modulus via a linear softening model.

Assumptions:
- Linear thermoelasticity
- 1D stress state (uniaxial)
- Small deformations
- No external mechanical loads (thermal loads only)
"""

import numpy as np


def compute_thermal_strain(temperature, T_ref, alpha_expansion):
    """
    Compute thermal strain at each point.

    Thermal strain: eps_th = alpha * (T - T_ref)

    Parameters
    ----------
    temperature : np.ndarray
        Temperature field [K], shape (n_cells,).
    T_ref : float
        Stress-free reference temperature [K].
    alpha_expansion : float
        Coefficient of thermal expansion [1/K].

    Returns
    -------
    np.ndarray
        Thermal strain (dimensionless), shape (n_cells,).
    """
    return alpha_expansion * (temperature - T_ref)


def compute_thermal_stress(temperature, T_ref, alpha_expansion, youngs_modulus):
    """
    Compute thermal stress for a fully constrained (fixed-fixed) bar.

    For a bar constrained at both ends with no mechanical strain allowed,
    the thermal stress is:
        sigma = -E * alpha * (T - T_ref)

    The negative sign indicates that heating produces compressive stress
    when expansion is constrained.

    Parameters
    ----------
    temperature : np.ndarray
        Temperature field [K], shape (n_cells,).
    T_ref : float
        Stress-free reference temperature [K].
    alpha_expansion : float
        Coefficient of thermal expansion [1/K].
    youngs_modulus : float or np.ndarray
        Young's modulus [Pa]. Can be spatially varying (temperature-dependent).

    Returns
    -------
    np.ndarray
        Thermal stress [Pa], shape (n_cells,). Negative = compressive.
    """
    return -youngs_modulus * alpha_expansion * (temperature - T_ref)


def compute_temperature_dependent_modulus(temperature, E_ref, T_ref, beta):
    """
    Compute temperature-dependent Young's modulus using linear softening.

    Model: E(T) = E_ref * (1 - beta * (T - T_ref))

    This captures the reduction of stiffness with increasing temperature.
    Valid for moderate temperature ranges where the linear approximation holds.

    Parameters
    ----------
    temperature : float or np.ndarray
        Temperature [K].
    E_ref : float
        Reference Young's modulus at T_ref [Pa].
    T_ref : float
        Reference temperature [K].
    beta : float
        Softening coefficient [1/K]. Typical values: 1e-4 to 5e-4 for metals.

    Returns
    -------
    float or np.ndarray
        Young's modulus at given temperature [Pa].
    """
    return E_ref * (1.0 - beta * (temperature - T_ref))


def compute_free_expansion_displacement(temperature, T_ref, alpha_expansion, dx):
    """
    Compute displacement field for free (unconstrained) thermal expansion.

    Integrates thermal strain from the left end (assumed fixed at x=0):
        u(x) = integral_0^x alpha*(T(x') - T_ref) dx'

    Uses trapezoidal integration over the cell centers.

    Parameters
    ----------
    temperature : np.ndarray
        Temperature field [K], shape (n_cells,).
    T_ref : float
        Reference temperature [K].
    alpha_expansion : float
        Coefficient of thermal expansion [1/K].
    dx : float
        Cell width [m] (uniform mesh assumed).

    Returns
    -------
    np.ndarray
        Displacement at each cell center [m], shape (n_cells,).
        u[0] ≈ 0 (fixed left end).
    """
    thermal_strain = alpha_expansion * (temperature - T_ref)

    # Cumulative integration using trapezoidal rule
    # Displacement at cell center i = sum of strain * dx from cell 0 to i-1
    # plus half the current cell's contribution
    displacement = np.zeros_like(temperature)
    for i in range(1, len(temperature)):
        displacement[i] = displacement[i - 1] + 0.5 * (thermal_strain[i - 1] + thermal_strain[i]) * dx

    return displacement


def compute_von_mises_equivalent(stress_xx):
    """
    Compute von Mises equivalent stress for 1D stress state.

    For uniaxial stress, von Mises = |sigma_xx|.

    Parameters
    ----------
    stress_xx : np.ndarray
        Axial stress [Pa].

    Returns
    -------
    np.ndarray
        Von Mises equivalent stress [Pa] (always non-negative).
    """
    return np.abs(stress_xx)


def compute_mechanical_results(temperature, T_ref, alpha_expansion, youngs_modulus,
                               dx, constrained=True):
    """
    Compute all mechanical quantities for the thermal-mechanical analysis.

    Parameters
    ----------
    temperature : np.ndarray
        Temperature field [K].
    T_ref : float
        Reference temperature [K].
    alpha_expansion : float
        Coefficient of thermal expansion [1/K].
    youngs_modulus : float or np.ndarray
        Young's modulus [Pa].
    dx : float
        Cell width [m].
    constrained : bool
        If True, compute stress for a fully constrained bar.
        If False, compute displacement for free expansion.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'thermal_strain': thermal strain field
        - 'thermal_stress': stress field (if constrained)
        - 'displacement': displacement field (if not constrained)
        - 'von_mises': von Mises equivalent stress
        - 'max_stress': maximum absolute stress value [Pa]
    """
    thermal_strain = compute_thermal_strain(temperature, T_ref, alpha_expansion)

    results = {'thermal_strain': thermal_strain}

    if constrained:
        stress = compute_thermal_stress(temperature, T_ref, alpha_expansion, youngs_modulus)
        results['thermal_stress'] = stress
        results['displacement'] = np.zeros_like(temperature)  # no displacement if fully constrained
        results['von_mises'] = compute_von_mises_equivalent(stress)
        results['max_stress'] = np.max(np.abs(stress))
    else:
        displacement = compute_free_expansion_displacement(temperature, T_ref, alpha_expansion, dx)
        results['displacement'] = displacement
        results['thermal_stress'] = np.zeros_like(temperature)  # no stress if free
        results['von_mises'] = np.zeros_like(temperature)
        results['max_stress'] = 0.0

    return results
