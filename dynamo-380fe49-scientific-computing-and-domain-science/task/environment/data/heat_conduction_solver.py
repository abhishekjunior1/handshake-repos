"""
heat_conduction_solver.py
=========================
Implicit theta-scheme finite difference solver for 1D transient heat conduction.

Solves the heat equation:
    rho * cp * dT/dt = d/dx(k * dT/dx) + Q

using a theta-scheme (theta=1: fully implicit, theta=0.5: Crank-Nicolson).

The solver builds a tridiagonal system and solves it with the Thomas algorithm
(TDMA - TriDiagonal Matrix Algorithm). The solver is generic — it takes
pre-computed face conductivities, source terms, and boundary conditions
as inputs and produces the temperature field at the next time level.
"""

import numpy as np


def thomas_algorithm(a, b, c, d):
    """
    Solve a tridiagonal system using the Thomas algorithm (TDMA).

    Solves [A]{x} = {d} where A is tridiagonal with:
        - a[i]: sub-diagonal (lower), i = 1..n-1 (a[0] unused)
        - b[i]: main diagonal, i = 0..n-1
        - c[i]: super-diagonal (upper), i = 0..n-2 (c[n-1] unused)

    Parameters
    ----------
    a : np.ndarray
        Sub-diagonal coefficients, shape (n,). a[0] is not used.
    b : np.ndarray
        Main diagonal coefficients, shape (n,).
    c : np.ndarray
        Super-diagonal coefficients, shape (n,). c[n-1] is not used.
    d : np.ndarray
        Right-hand side vector, shape (n,).

    Returns
    -------
    np.ndarray
        Solution vector x, shape (n,).
    """
    n = len(d)
    # Make copies to avoid modifying input arrays
    c_prime = np.zeros(n)
    d_prime = np.zeros(n)

    # Forward sweep
    c_prime[0] = c[0] / b[0]
    d_prime[0] = d[0] / b[0]

    for i in range(1, n):
        denom = b[i] - a[i] * c_prime[i - 1]
        c_prime[i] = c[i] / denom if i < n - 1 else 0.0
        d_prime[i] = (d[i] - a[i] * d_prime[i - 1]) / denom

    # Back substitution
    x = np.zeros(n)
    x[n - 1] = d_prime[n - 1]

    for i in range(n - 2, -1, -1):
        x[i] = d_prime[i] - c_prime[i] * x[i + 1]

    return x


def build_tridiagonal_system(T_old, k_faces, rho, cp, dx, dt, source, theta,
                             bc_left, bc_right):
    """
    Build the tridiagonal system for the theta-scheme heat conduction equation.

    The discretized equation for interior cell i:
        rho*cp*dx/dt * (T_new[i] - T_old[i]) =
            theta * [k_{i+1/2}*(T_new[i+1]-T_new[i])/dx - k_{i-1/2}*(T_new[i]-T_new[i-1])/dx]
          + (1-theta) * [k_{i+1/2}*(T_old[i+1]-T_old[i])/dx - k_{i-1/2}*(T_old[i]-T_old[i-1])/dx]
          + source[i] * dx

    Parameters
    ----------
    T_old : np.ndarray
        Temperature at current time level [K], shape (n_cells,).
    k_faces : np.ndarray
        Thermal conductivity at cell faces [W/(m·K)], shape (n_cells - 1,).
        k_faces[i] is the conductivity at the face between cell i and cell i+1.
    rho : float or np.ndarray
        Density [kg/m^3].
    cp : float or np.ndarray
        Specific heat [J/(kg·K)].
    dx : float
        Cell width [m].
    dt : float
        Time step [s].
    source : np.ndarray
        Volumetric source term [W/m^3], shape (n_cells,).
    theta : float
        Implicitness parameter (0=explicit, 0.5=Crank-Nicolson, 1=fully implicit).
    bc_left : dict
        Left boundary condition. Keys: 'type' ('dirichlet' or 'neumann'),
        'value' (temperature [K] or heat flux [W/m^2]).
    bc_right : dict
        Right boundary condition. Same format as bc_left.

    Returns
    -------
    tuple of (np.ndarray, np.ndarray, np.ndarray, np.ndarray)
        (a, b, c, d) arrays for the Thomas algorithm.
    """
    n = len(T_old)
    a = np.zeros(n)  # sub-diagonal
    b = np.zeros(n)  # main diagonal
    c = np.zeros(n)  # super-diagonal
    d = np.zeros(n)  # RHS

    # Thermal capacity coefficient
    if np.isscalar(rho) and np.isscalar(cp):
        alpha_cap = rho * cp * dx / dt
    else:
        alpha_cap = np.asarray(rho) * np.asarray(cp) * dx / dt

    # Build interior equations (cells 1 to n-2)
    for i in range(1, n - 1):
        k_left = k_faces[i - 1]   # face between cell i-1 and cell i
        k_right = k_faces[i]      # face between cell i and cell i+1

        # Implicit part (theta-weighted)
        a[i] = -theta * k_left / dx
        c[i] = -theta * k_right / dx
        b[i] = alpha_cap + theta * (k_left + k_right) / dx

        # Explicit part ((1-theta)-weighted) contributes to RHS
        explicit_flux = ((1.0 - theta) * k_right / dx * (T_old[i + 1] - T_old[i])
                        - (1.0 - theta) * k_left / dx * (T_old[i] - T_old[i - 1]))

        d[i] = alpha_cap * T_old[i] + explicit_flux + source[i] * dx

    # --- Left boundary (cell 0) ---
    if bc_left['type'] == 'dirichlet':
        b[0] = 1.0
        c[0] = 0.0
        a[0] = 0.0
        d[0] = bc_left['value']
    elif bc_left['type'] == 'neumann':
        # Neumann: specified heat flux at left boundary
        # q = -k * dT/dx at x=0 (positive q means heat flowing in)
        k_right = k_faces[0]
        b[0] = alpha_cap + theta * k_right / dx
        c[0] = -theta * k_right / dx
        explicit_flux = (1.0 - theta) * k_right / dx * (T_old[1] - T_old[0])
        d[0] = alpha_cap * T_old[0] + explicit_flux + source[0] * dx + bc_left['value']

    # --- Right boundary (cell n-1) ---
    if bc_right['type'] == 'dirichlet':
        b[n - 1] = 1.0
        a[n - 1] = 0.0
        c[n - 1] = 0.0
        d[n - 1] = bc_right['value']
    elif bc_right['type'] == 'neumann':
        # Neumann: specified heat flux at right boundary
        k_left = k_faces[n - 2]
        a[n - 1] = -theta * k_left / dx
        b[n - 1] = alpha_cap + theta * k_left / dx
        explicit_flux = -(1.0 - theta) * k_left / dx * (T_old[n - 1] - T_old[n - 2])
        d[n - 1] = alpha_cap * T_old[n - 1] + explicit_flux + source[n - 1] * dx + bc_right['value']

    return a, b, c, d


def solve_heat_conduction(T_old, k_faces, rho, cp, dx, dt, source, theta,
                          bc_left, bc_right):
    """
    Solve one time step of the 1D heat conduction equation.

    This is the main entry point for the heat conduction solver. It assembles
    the tridiagonal system and solves it using the Thomas algorithm.

    Parameters
    ----------
    T_old : np.ndarray
        Temperature at current time level [K], shape (n_cells,).
    k_faces : np.ndarray
        Thermal conductivity at internal cell faces [W/(m·K)], shape (n_cells - 1,).
    rho : float or np.ndarray
        Density [kg/m^3].
    cp : float or np.ndarray
        Specific heat [J/(kg·K)].
    dx : float
        Cell width [m].
    dt : float
        Time step [s].
    source : np.ndarray
        Volumetric source term [W/m^3], shape (n_cells,).
    theta : float
        Implicitness parameter (1.0 for fully implicit recommended for stability).
    bc_left : dict
        Left boundary condition dict with 'type' and 'value'.
    bc_right : dict
        Right boundary condition dict with 'type' and 'value'.

    Returns
    -------
    np.ndarray
        Temperature at new time level [K], shape (n_cells,).
    """
    a, b, c, d = build_tridiagonal_system(
        T_old, k_faces, rho, cp, dx, dt, source, theta, bc_left, bc_right
    )
    T_new = thomas_algorithm(a, b, c, d)
    return T_new


def compute_energy_balance(T_old, T_new, rho, cp, dx, source, dt, cross_section_area):
    """
    Compute the energy balance error for verification.

    Energy stored = Energy from sources + net boundary flux
    Error = |stored - (sources + boundary)| / max(|stored|, eps)

    Parameters
    ----------
    T_old : np.ndarray
        Temperature at old time level [K].
    T_new : np.ndarray
        Temperature at new time level [K].
    rho : float
        Density [kg/m^3].
    cp : float or np.ndarray
        Specific heat [J/(kg·K)].
    dx : float
        Cell width [m].
    source : np.ndarray
        Volumetric heat source [W/m^3].
    dt : float
        Time step [s].
    cross_section_area : float
        Cross-sectional area [m^2].

    Returns
    -------
    float
        Total energy stored in the domain over this time step [J].
    """
    # Energy stored = rho * cp * (T_new - T_old) * volume
    cell_volume = dx * cross_section_area
    energy_stored = np.sum(rho * cp * (T_new - T_old) * cell_volume)
    return energy_stored
