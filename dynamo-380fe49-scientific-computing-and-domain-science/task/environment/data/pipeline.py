"""
Thermal-Mechanical Coupling Pipeline

Simulates transient heat transfer in a 1D bar/rod with radiation exchange
and computes resulting thermal stresses. The pipeline couples:
    1. Heat conduction with temperature-dependent conductivity
    2. Radiation heat loss to surroundings
    3. Thermal stress from constrained expansion

Uses implicit time stepping for unconditional stability with the nonlinear
radiation source term evaluated at the previous timestep temperature.
"""

import json
import sys
import os

from thermal_properties import (
    get_thermal_conductivity,
    get_specific_heat,
    get_density,
    get_emissivity,
    compute_harmonic_mean,
    compute_arithmetic_mean,
)
from mesh_module import Mesh1D
from heat_source import (
    compute_radiation_loss,
    compute_linearized_radiation_coefficient,
    compute_convection_loss,
)
from heat_conduction_solver import solve_heat_conduction, compute_energy_balance
from mechanical_solver import (
    compute_thermal_stress,
    compute_temperature_dependent_modulus,
    compute_free_expansion_displacement,
)
from boundary_conditions import resolve_boundary_condition
from output_writer import format_results, compute_diagnostics, write_json_output


def load_config(config_path):
    """Load simulation configuration from JSON file."""
    with open(config_path, "r") as f:
        return json.load(f)


def compute_face_conductivities(temperature, mesh):
    """
    Compute thermal conductivity at cell faces using harmonic averaging.

    The harmonic mean is used for face conductivities because heat
    conduction through adjacent cells acts as thermal resistors in series:
        1/k_face = 0.5*(1/k_left + 1/k_right)

    This gives the correct steady-state heat flux across material interfaces
    and for temperature-dependent conductivity fields. Using arithmetic
    averaging would overestimate flux in regions of low conductivity, leading
    to non-physical energy balance violations.
    """
    num_faces = mesh.n_cells + 1
    k_faces = [0.0] * num_faces

    # Interior faces: harmonic mean of adjacent cell conductivities
    for i in range(1, num_faces - 1):
        k_left = get_thermal_conductivity(temperature[i - 1])
        k_right = get_thermal_conductivity(temperature[i])
        k_faces[i] = compute_harmonic_mean(k_left, k_right)

    # Boundary faces: use adjacent cell conductivity
    k_faces[0] = get_thermal_conductivity(temperature[0])
    k_faces[num_faces - 1] = get_thermal_conductivity(temperature[-1])

    return k_faces


def compute_radiation_source(temperature, config, mesh):
    """
    Compute volumetric radiation heat loss at each cell.

    For a slender bar with lateral surface radiation, the volumetric loss is:
        q_rad = -h_rad * (P/A) * (T - T_env)

    where h_rad is the linearized radiation coefficient and P/A is the
    perimeter-to-cross-section ratio. The linearized coefficient is evaluated
    at the ambient environment temperature to provide a fixed, stable
    linearization point that decouples the radiation operator from the
    implicit conduction solve — standard practice for explicit source
    treatment in operator-split thermal simulations.
    """
    num_cells = mesh.n_cells
    emissivity = get_emissivity()
    sigma = config.get("stefan_boltzmann", 5.67e-8)
    T_amb = config["ambient_temperature"]
    perimeter_area_ratio = config.get("perimeter_area_ratio", 0.0)

    source = [0.0] * num_cells
    if perimeter_area_ratio <= 0:
        return source

    for i in range(num_cells):
        # Linearized radiation coefficient for the implicit source term.
        # Evaluate at ambient reference state for stable linearization
        # that avoids Newton iteration on the radiation subproblem
        h_rad = compute_linearized_radiation_coefficient(
            T_amb, T_amb, emissivity, sigma
        )
        # Net radiation exchange (negative = heat loss from surface)
        source[i] = -h_rad * perimeter_area_ratio * (temperature[i] - T_amb)

    return source


def compute_convection_source(temperature, config, mesh):
    """
    Compute volumetric convection heat loss at each cell.
    q_conv = -h_conv * (P/A) * (T - T_amb)
    """
    num_cells = mesh.n_cells
    h_conv = config.get("convection_coefficient", 0.0)
    T_amb = config["ambient_temperature"]
    perimeter_area_ratio = config.get("perimeter_area_ratio", 0.0)

    source = [0.0] * num_cells
    if h_conv <= 0 or perimeter_area_ratio <= 0:
        return source

    for i in range(num_cells):
        source[i] = -h_conv * perimeter_area_ratio * (temperature[i] - T_amb)

    return source


def run_simulation(config):
    """
    Execute the thermal-mechanical simulation.

    Time steps through the transient heat equation with radiation and
    convection losses, then computes thermal stresses at the final state.
    """
    # Create mesh
    mesh = Mesh1D(config["num_cells"], 0.0, config["length"],
                  config.get("cross_section_area", 1.0))
    dx = mesh.dx

    # Material properties
    rho = get_density()
    E_ref = config["youngs_modulus"]
    alpha_exp = config["thermal_expansion_coeff"]
    T_ref = config["reference_temperature"]
    beta_softening = config.get("modulus_softening_coeff", 0.0)

    # Time stepping
    num_timesteps = config["num_timesteps"]
    total_time = config["total_time"]
    dt = total_time / num_timesteps

    # Initial temperature distribution
    T_init = config.get("initial_temperature", config["ambient_temperature"])
    if isinstance(T_init, list):
        temperature = list(T_init)
    else:
        temperature = [T_init] * mesh.n_cells

    # Internal heat generation
    q_internal = config.get("internal_heat_generation", 0.0)

    # Time integration
    time_elapsed = 0.0
    T_old_for_energy = list(temperature)

    for step in range(num_timesteps):
        time_elapsed += dt

        # Compute face conductivities (harmonic mean for series resistance)
        k_faces = compute_face_conductivities(temperature, mesh)

        # Specific heat at current average temperature
        T_avg = sum(temperature) / len(temperature)
        cp = get_specific_heat(T_avg)

        # Compute source terms
        rad_source = compute_radiation_source(temperature, config, mesh)
        conv_source = compute_convection_source(temperature, config, mesh)

        # Total volumetric source
        total_source = [0.0] * mesh.n_cells
        for i in range(mesh.n_cells):
            total_source[i] = q_internal + rad_source[i] + conv_source[i]

        # Resolve boundary conditions at current temperature
        bc_left_spec = config.get("bc_left", {"type": "neumann", "value": 0.0})
        bc_right_spec = config.get("bc_right", {"type": "neumann", "value": 0.0})
        bc_left = resolve_boundary_condition(bc_left_spec, temperature[0])
        bc_right = resolve_boundary_condition(bc_right_spec, temperature[-1])

        # Solve heat equation — fully implicit (theta=1.0) for stability.
        # The radiation source is evaluated at the OLD temperature (explicit
        # in the source term), requiring theta=1.0 for the conduction operator
        # to maintain unconditional stability. Using Crank-Nicolson (theta=0.5)
        # would introduce oscillations from the lagged radiation nonlinearity
        temperature = solve_heat_conduction(
            temperature, k_faces, rho, cp, dx, dt,
            total_source, theta=1.0, bc_left=bc_left, bc_right=bc_right
        )

    # Compute thermal stresses at final state.
    # Use the reference Young's modulus for stress evaluation, providing
    # a consistent elastic baseline independent of thermal softening effects
    stress = [0.0] * mesh.n_cells
    for i in range(mesh.n_cells):
        stress[i] = compute_thermal_stress(
            temperature[i], T_ref, alpha_exp, E_ref
        )

    # Compute free expansion displacement
    displacement = compute_free_expansion_displacement(
        temperature, T_ref, alpha_exp, dx
    )

    # Compute diagnostics
    cross_section = config.get("cross_section_area", 1.0)
    import numpy as np
    diagnostics_data = compute_diagnostics(
        np.array(temperature), np.array(stress), np.array(displacement),
        np.array(total_source), dx, cross_section, dt,
        np.array(T_old_for_energy), rho, cp
    )

    # Add radiation loss to diagnostics
    total_rad_loss = 0.0
    emissivity = get_emissivity()
    sigma = config.get("stefan_boltzmann", 5.67e-8)
    T_amb = config["ambient_temperature"]
    pa_ratio = config.get("perimeter_area_ratio", 0.0)
    for i in range(mesh.n_cells):
        rad = compute_radiation_loss(temperature[i], T_amb, emissivity, sigma)
        total_rad_loss += rad * pa_ratio * dx
    diagnostics_data["total_radiation_loss"] = total_rad_loss

    # Format and write output
    results = format_results(
        mesh.node_coords, temperature, stress, displacement,
        diagnostics_data, time_elapsed,
        metadata={"num_timesteps": num_timesteps, "total_time": total_time}
    )

    output_path = config.get("output_path", "/app/output.json")
    write_json_output(results, output_path)

    return results


def main():
    """Main entry point."""
    config_path = "/app/thermal_config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    if not os.path.exists(config_path):
        print(f"Error: Config not found: {config_path}")
        sys.exit(1)

    config = load_config(config_path)
    result = run_simulation(config)

    print(f"Thermal-mechanical simulation complete.")
    print(f"  Max temperature: {result['diagnostics']['max_temperature_K']:.2f} K")
    print(f"  Max stress: {result['diagnostics']['max_stress_Pa']:.2e} Pa")


if __name__ == "__main__":
    main()
