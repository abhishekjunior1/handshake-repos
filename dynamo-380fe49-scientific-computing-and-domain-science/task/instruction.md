A thermal-mechanical coupling pipeline at `/app/pipeline.py` simulates transient heat transfer with radiation exchange and computes resulting thermal stresses in a 1D bar. It uses modules `/app/thermal_properties.py`, `/app/mesh_module.py`, `/app/heat_source.py`, `/app/heat_conduction_solver.py`, `/app/mechanical_solver.py`, `/app/boundary_conditions.py`, and `/app/output_writer.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/thermal_config.json` and writes `/app/output.json`.

The pipeline solves the transient heat equation with temperature-dependent thermal conductivity, lateral radiation and convection losses, and internal heat generation. After the thermal solution converges, it computes thermal stresses using temperature-dependent material properties. The `modulus_softening_coeff` parameter controls how Young's modulus decreases with temperature: E(T) = E_ref * (1 - beta * (T - T_ref)).

The pipeline produces correct output on the current configuration but has bugs that cause incorrect results on configurations with active radiation exchange and temperature-dependent mechanical properties. Find and fix the bugs so the pipeline handles all valid configurations correctly.

Do not rewrite from scratch — preserve the existing module structure and numerical methods. In particular, preserve the harmonic mean averaging for face conductivities (correct for the series thermal resistance analogy) and the fully implicit time stepping (theta=1.0, required for stability with the lagged radiation source term). The fixed pipeline will be tested on a different configuration than the one at `/app/thermal_config.json`.

Output: `/app/output.json` — a JSON object with fields: `simulation_time_s` (float), `n_cells` (int), `profiles` (object with arrays `x_coordinates_m`, `temperature_K`, `thermal_stress_Pa`, `displacement_m`), `diagnostics` (object with `max_temperature_K`, `min_temperature_K`, `max_stress_Pa`, `max_displacement_m`, `total_heat_source_W`, `energy_stored_J`, `energy_from_sources_J`, `energy_balance_error`, `total_radiation_loss`), and `metadata` (object with `num_timesteps`, `total_time`).
