"""
Hotplug Reporter — formats the final output JSON for the virtio device
hotplug controller pipeline.
"""

import json
from typing import Any


class HotplugReporter:
    """Formats and writes the pipeline output report."""

    def __init__(self, output_path: str = "/app/output.json"):
        """Initialize reporter with output file path."""
        self._output_path = output_path
        self._sections: dict[str, Any] = {}

    def add_section(self, name: str, data: Any) -> None:
        """Add a named section to the report."""
        self._sections[name] = data

    def generate_report(self) -> dict:
        """Generate the complete pipeline output report."""
        report = {
            "pipeline_status": "completed",
            "stages": {},
        }

        # Order sections by pipeline stage
        stage_order = [
            "device_registry",
            "capability_negotiation",
            "queue_configuration",
            "dma_mappings",
            "migration_state",
        ]

        for stage in stage_order:
            if stage in self._sections:
                report["stages"][stage] = self._sections[stage]

        # Include any additional sections not in the standard order
        for name, data in self._sections.items():
            if name not in stage_order:
                report["stages"][name] = data

        return report

    def write_report(self) -> str:
        """Write the report to the configured output path."""
        report = self.generate_report()
        json_output = json.dumps(report, indent=2)

        with open(self._output_path, "w") as f:
            f.write(json_output)
            f.write("\n")

        return json_output

    def get_output_path(self) -> str:
        """Return the configured output path."""
        return self._output_path
