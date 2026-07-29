A sensor fusion and motor control pipeline at `/app/pipeline.py` processes raw IMU data through calibration, complementary filter orientation estimation, fault detection, and PID motor control. It uses modules `/app/config_loader.py`, `/app/sensor_reader.py`, `/app/calibration.py`, `/app/fusion_engine.py`, `/app/fault_detector.py`, `/app/motor_controller.py`, and `/app/telemetry.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/sensor_config.json` and writes `/app/output.json`.

The pipeline produces correct output on the current sensor configuration but has bugs that cause incorrect orientation estimates, motor commands, and fault detection results when processing different sensor data with non-trivial calibration parameters. Find and fix the bugs so the pipeline handles all valid sensor configurations correctly.

Do not rewrite from scratch — preserve the existing module structure, the trapezoidal PID integration method, and the WXYZ quaternion packing order. The fixed pipeline will be tested on a different sensor configuration than the one at `/app/sensor_config.json`.

Output: `/app/output.json` — JSON with `pipeline_version`, `total_frames`, `summary` (containing `final_orientation_wxyz`, `average_motor_output`, `total_fault_events`, `frames_processed`), and `frames` array where each frame has `orientation_wxyz`, `euler_deg`, `motor_commands`, `control` diagnostics, `calibrated` sensor values, and `health` status with per-sensor fault details.
