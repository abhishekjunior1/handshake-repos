"""
Solution for the thermal-mechanical coupling pipeline.

Fixes two value-passing bugs in pipeline.py:

1. The radiation linearization coefficient is computed using T_amb for both
   arguments: compute_linearized_radiation_coefficient(T_amb, T_amb, ...).
   It should use the current cell temperature as the first argument:
   compute_linearized_radiation_coefficient(temperature[i], T_amb, ...).
   The linearization h_rad = eps*sigma*(T_s^2 + T_e^2)*(T_s + T_e) requires
   the actual surface temperature for accurate radiation exchange.

2. The thermal stress computation uses the constant reference Young's modulus
   E_ref instead of the temperature-dependent modulus E(T). For materials with
   thermal softening (beta > 0), E decreases with temperature:
   E(T) = E_ref * (1 - beta * (T - T_ref)). The pipeline should call
   compute_temperature_dependent_modulus() and pass the result to
   compute_thermal_stress().
"""

import os


def apply_fix():
    pipeline_path = "/app/pipeline.py"

    with open(pipeline_path, "r") as f:
        content = f.read()

    # Fix 1: Radiation linearization should use temperature[i], not T_amb
    old_radiation = '''        # Linearized radiation coefficient for the implicit source term.
        # Evaluate at ambient reference state for stable linearization
        # that avoids Newton iteration on the radiation subproblem
        h_rad = compute_linearized_radiation_coefficient(
            T_amb, T_amb, emissivity, sigma
        )'''

    new_radiation = '''        # Linearized radiation coefficient at current surface temperature
        h_rad = compute_linearized_radiation_coefficient(
            temperature[i], T_amb, emissivity, sigma
        )'''

    content = content.replace(old_radiation, new_radiation)

    # Fix 2: Use temperature-dependent modulus for stress
    old_stress = '''    # Compute thermal stresses at final state.
    # Use the reference Young's modulus for stress evaluation, providing
    # a consistent elastic baseline independent of thermal softening effects
    stress = [0.0] * mesh.n_cells
    for i in range(mesh.n_cells):
        stress[i] = compute_thermal_stress(
            temperature[i], T_ref, alpha_exp, E_ref
        )'''

    new_stress = '''    # Compute thermal stresses at final state with temperature-dependent modulus
    stress = [0.0] * mesh.n_cells
    for i in range(mesh.n_cells):
        E_T = compute_temperature_dependent_modulus(
            temperature[i], E_ref, T_ref, beta_softening
        )
        stress[i] = compute_thermal_stress(
            temperature[i], T_ref, alpha_exp, E_T
        )'''

    content = content.replace(old_stress, new_stress)

    with open(pipeline_path, "w") as f:
        f.write(content)

    print("Applied fixes to pipeline.py")
    print("  Fix 1: Radiation linearization uses current temperature")
    print("  Fix 2: Thermal stress uses temperature-dependent modulus")


if __name__ == "__main__":
    apply_fix()
    os.system("cd /app && python3 pipeline.py")
