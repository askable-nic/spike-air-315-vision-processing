Run an agent-based experiment evaluation using parallel claude -p subprocesses.

## Arguments

$ARGUMENTS — Passed directly to `python src/agent_experiment.py`. Supports:
- `--branch/-b <name>` (required) — Experiment branch
- `--iteration/-i <num>` — Iteration number (default: latest)
- `--session/-s <id>` — Session ID (repeatable, default: all with baselines)
- `--force/-f` — Force re-extraction
- `--budget <usd>` — Max budget per agent in USD (default: 0.50)

Examples:
- `--branch visual-change-driven --iteration 3`
- `-b visual-change-driven -i 3 -s travel_expert_lisa`
- `-b visual-change-driven --budget 1.00`

## Instructions

1. Run the orchestrator:
   ```
   python src/agent_experiment.py $ARGUMENTS
   ```

2. When it completes, read the experiment summary:
   - `experiments/<branch>/<iteration>/output/experiment_summary.json`
   - `experiments/<branch>/<iteration>/output/experiment_summary.md`

3. Present results to the user:
   - Headline aggregate metrics (F1, recall, precision)
   - Per-session breakdown: F1, severity, key issues
   - Whether canary gated or any sessions were aborted
   - Top patterns and recommendations if available
