"""
output_writer.py
================
Output formatting and JSON writer for 1D thermal-mechanical simulation results.

Formats temperature profiles, stress profiles, displacement fields, and
diagnostic quantities into structured JSON output for post-processing
and visualization.
"""

import json
import numpy as np


class NumpyEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles NumPy arrays and data types.

    Converts numpy arrays to lists and numpy scalars to Python native types
    for JSON serialization.
    """

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        return super().default(obj)


def compute_diagnostics(temperature, stress, displacement, heat_source,
                        dx, cross_section_area, dt, T_old, rho, cp):
    """
    Compute diagnostic quantities for simulation verification.

    Parameters
    ----------
    temperature : np.ndarray
        Final temperature profile [K].
    stress : np.ndarray
        Thermal stress profile [Pa].
    displacement : np.ndarray
        Displacement profile [m].
    heat_source : np.ndarray
        Volumetric heat source [W/m^3].
    dx : float
        Cell width [m].
    cross_section_area : float
        Cross-sectional area [m^2].
    dt : float
        Time step [s].
    T_old : np.ndarray
        Previous temperature profile [K].
    rho : float
        Density [kg/m^3].
    cp : float or np.ndarray
        Specific heat [J/(kg·K)].

    Returns
    -------
    dict
        Diagnostic quantities including max temperature, max stress,
        total heat source, and energy balance error.
    """
    cell_volume = dx * cross_section_area

    # Maximum values
    max_temp = float(np.max(temperature))
    min_temp = float(np.min(temperature))
    max_stress = float(np.max(np.abs(stress)))
    max_displacement = float(np.max(np.abs(displacement)))

    # Total heat source power [W]
    total_heat_source = float(np.sum(heat_source * cell_volume))

    # Energy stored this time step [J]
    energy_stored = float(np.sum(rho * cp * (temperature - T_old) * cell_volume))

    # Energy from sources [J]
    energy_from_sources = total_heat_source * dt

    # Energy balance error (relative)
    if abs(energy_stored) > 1e-30:
        energy_balance_error = abs(energy_stored - energy_from_sources) / abs(energy_stored)
    else:
        energy_balance_error = 0.0

    return {
        'max_temperature_K': max_temp,
        'min_temperature_K': min_temp,
        'max_stress_Pa': max_stress,
        'max_displacement_m': max_displacement,
        'total_heat_source_W': total_heat_source,
        'energy_stored_J': energy_stored,
        'energy_from_sources_J': energy_from_sources,
        'energy_balance_error': energy_balance_error,
    }


def format_results(x_coords, temperature, stress, displacement, diagnostics,
                   time, metadata=None):
    """
    Format simulation results into a structured dictionary.

    Parameters
    ----------
    x_coords : np.ndarray
        Cell center coordinates [m].
    temperature : np.ndarray
        Temperature profile [K].
    stress : np.ndarray
        Thermal stress profile [Pa].
    displacement : np.ndarray
        Displacement profile [m].
    diagnostics : dict
        Diagnostic quantities from compute_diagnostics().
    time : float
        Current simulation time [s].
    metadata : dict, optional
        Additional metadata (solver parameters, material properties, etc.).

    Returns
    -------
    dict
        Structured results dictionary ready for JSON serialization.
    """
    results = {
        'simulation_time_s': float(time),
        'n_cells': len(x_coords),
        'profiles': {
            'x_coordinates_m': x_coords,
            'temperature_K': temperature,
            'thermal_stress_Pa': stress,
            'displacement_m': displacement,
        },
        'diagnostics': diagnostics,
    }

    if metadata is not None:
        results['metadata'] = metadata

    return results


def write_json_output(results, filepath):
    """
    Write simulation results to a JSON file.

    Parameters
    ----------
    results : dict
        Structured results from format_results().
    filepath : str
        Output file path.
    """
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, cls=NumpyEncoder)


def write_results_to_string(results):
    """
    Serialize simulation results to a JSON string.

    Parameters
    ----------
    results : dict
        Structured results from format_results().

    Returns
    -------
    str
        JSON-formatted string.
    """
    return json.dumps(results, indent=2, cls=NumpyEncoder)


def print_summary(diagnostics, time):
    """
    Print a human-readable summary of simulation diagnostics.

    Parameters
    ----------
    diagnostics : dict
        Diagnostic quantities.
    time : float
        Current simulation time [s].
    """
    print(f"{'='*60}")
    print(f"  Simulation Results at t = {time:.4e} s")
    print(f"{'='*60}")
    print(f"  Max Temperature:    {diagnostics['max_temperature_K']:.2f} K")
    print(f"  Min Temperature:    {diagnostics['min_temperature_K']:.2f} K")
    print(f"  Max Stress:         {diagnostics['max_stress_Pa']:.4e} Pa")
    print(f"  Max Displacement:   {diagnostics['max_displacement_m']:.4e} m")
    print(f"  Total Heat Source:  {diagnostics['total_heat_source_W']:.4e} W")
    print(f"  Energy Balance Err: {diagnostics['energy_balance_error']:.4e}")
    print(f"{'='*60}")
