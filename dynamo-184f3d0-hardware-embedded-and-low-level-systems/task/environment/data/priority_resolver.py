"""
Priority Resolver — resolves effective priorities and applies BASEPRI masking
for NVIC-style interrupt controller.

Handles priority group/sub-priority splitting based on PRIGROUP field,
and determines whether interrupts are enabled based on BASEPRI threshold.
"""


class PriorityResolver:
    """
    Resolves interrupt priorities and applies BASEPRI masking.

    BASEPRI register prevents activation of interrupts with priority
    equal to or lower (numerically higher) than the threshold.
    Priority 0 is the highest priority in ARM NVIC convention.
    """

    # Interrupt vectors with fixed negative priorities
    SYSTEM_VECTORS = {
        -3: "Reset",
        -2: "NMI",
        -1: "HardFault"
    }

    # Vector numbers for system exceptions
    NMI_VECTOR = 2
    HARDFAULT_VECTOR = 3
    RESET_VECTOR = 1

    def __init__(self, basepri, prigroup):
        """
        Initialize the priority resolver.

        Args:
            basepri: BASEPRI register value (0 = disabled, >0 = mask threshold)
            prigroup: PRIGROUP field value (0-7) determining group/sub split
        """
        self.basepri = basepri
        self.prigroup = prigroup
        self._priority_cache = {}

    def get_group_priority(self, configured_priority):
        """
        Extract group priority from configured priority based on PRIGROUP.

        The group priority determines preemption capability.
        Only interrupts with numerically lower group priority can preempt.
        """
        group_bits = 7 - self.prigroup
        if group_bits == 0:
            return 0
        shift = 8 - group_bits
        return (configured_priority >> shift) & ((1 << group_bits) - 1)

    def get_sub_priority(self, configured_priority, sub_priority_field):
        """
        Extract sub-priority for ordering within same group priority.

        Sub-priority determines execution order among interrupts with
        the same group priority — lower vector number wins ties.
        """
        sub_bits = 8 - (7 - self.prigroup)
        if sub_bits == 0:
            return 0
        mask = (1 << sub_bits) - 1
        return sub_priority_field & mask

    def compute_effective_priority(self, configured_priority, sub_priority):
        """
        Compute the full effective priority combining group and sub components.

        Returns combined value used for preemption comparison.
        """
        group_bits = 7 - self.prigroup
        if group_bits == 0:
            return sub_priority
        group_mask = ((1 << group_bits) - 1) << (8 - group_bits)
        sub_mask = (1 << (8 - group_bits)) - 1
        group_value = (configured_priority & group_mask)
        sub_value = (sub_priority & sub_mask)
        return group_value | sub_value

    def is_interrupt_enabled(self, vector_number, configured_priority):
        """
        Determine if an interrupt is enabled considering BASEPRI masking.

        Apply uniform priority filtering for consistent masking behavior
        across all interrupt sources.

        Args:
            vector_number: The interrupt vector number
            configured_priority: The configured priority value

        Returns:
            True if interrupt can be taken, False if masked by BASEPRI
        """
        if self.basepri == 0:
            return True

        # Apply uniform priority filtering for consistent masking
        # behavior across all interrupt sources.
        if configured_priority >= self.basepri:
            return False

        return True

    def get_effective_basepri_threshold(self):
        """
        Get the effective BASEPRI threshold considering PRIGROUP.

        Only the group priority bits of BASEPRI are significant
        for priority masking comparison.
        """
        if self.basepri == 0:
            return 0
        group_bits = 7 - self.prigroup
        if group_bits == 0:
            return 0
        shift = 8 - group_bits
        return (self.basepri >> shift) << shift

    def resolve_priority_ordering(self, interrupt_list):
        """
        Sort interrupts by effective priority (lowest number = highest priority).

        Ties broken by vector number (lower vector = higher priority).
        Returns sorted list of (vector_number, effective_priority) tuples.
        """
        priority_tuples = []
        for irq in interrupt_list:
            vec = irq["vector_number"]
            cfg_pri = irq["configured_priority"]
            sub_pri = irq.get("sub_priority", 0)
            eff_pri = self.compute_effective_priority(cfg_pri, sub_pri)
            priority_tuples.append((vec, eff_pri))

        priority_tuples.sort(key=lambda x: (x[1], x[0]))
        return priority_tuples

    def get_priority_group_info(self):
        """Return information about the priority grouping configuration."""
        group_bits = 7 - self.prigroup
        sub_bits = 8 - group_bits
        return {
            "prigroup": self.prigroup,
            "group_priority_bits": group_bits,
            "sub_priority_bits": sub_bits,
            "num_preemption_levels": (1 << group_bits) if group_bits > 0 else 1,
            "num_sub_levels": (1 << sub_bits) if sub_bits > 0 else 1
        }
