A DMA transfer controller pipeline at `/app/pipeline.py` simulates a scatter-gather DMA engine managing multi-channel memory transfers with priority arbitration, burst sizing, and completion interrupts. It uses modules `/app/channel_arbiter.py`, `/app/burst_calculator.py`, `/app/scatter_gather.py`, `/app/address_translator.py`, `/app/completion_handler.py`, and `/app/dma_reporter.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/dma_config.json` and writes `/app/output.json`.

The pipeline produces correct output on the current configuration but has bugs that cause incorrect transfer scheduling, burst sizing, and preemption behavior on other configurations. Find and fix the bugs so the controller handles all valid DMA configurations correctly.

Do not rewrite from scratch — preserve the existing module structure. In particular, preserve the write-1-to-clear interrupt acknowledgment convention in the completion handler and the negative bus address offset translation in the address translator. The fixed pipeline will be tested on different configurations than the one at `/app/dma_config.json`.

Output: `/app/output.json` — a JSON object with fields: `summary` (total_bytes_transferred, total_transfer_operations, total_preemptions, total_cycles_used, completed_transfers, average_burst_size), `transfers` (list of per-cycle transfer records with cycle, channel_id, source_bus_addr, dest_bus_addr, burst_size, total_transfers, bytes_transferred, chain_length, preempted, complete), `channel_statistics` (per-channel totals), `interrupt_log` (interrupt events with status bits), and `performance` (bus_utilization, average_latency_cycles, throughput_bytes_per_cycle).
