Run evaluation(s) and suggest improvements to the VEX pipeline.

You are the LLM judge. Instead of calling an external API for qualitative analysis, you perform the evaluation directly.

## Arguments

$ARGUMENTS — One or more `branch/iteration` pairs (e.g. `visual-change-driven/3`), optionally followed by session IDs. If no arguments, evaluate the most recent experiment iteration.

## Instructions

### Phase 1: Run extraction + mechanical metrics

1. **Parse arguments** to determine which branch/iteration(s) and optional session(s) to evaluate.
   - If no arguments given, look at `experiments/` to find the most recent branch/iteration with output.

2. **Run the experiment pipeline** to get extraction + mechanical metrics:
   ```
   vex experiment -b <branch> -i <iteration> [-s <session>]
   ```
   This runs extraction + mechanical evaluation (greedy matching, F1/precision/recall). Qualitative analysis is your job.

3. **Read the mechanical results**:
   - `experiments/<branch>/<iteration>/output/experiment_progress.json` — per-session metrics
   - `experiments/<branch>/<iteration>/output/experiment_summary.json` — aggregate metrics

### Phase 2: Read supporting context

In parallel, read:
- Experiment config: `experiments/<branch>/<iteration>/config.yaml` and `experiments/<branch>/config.yaml`
- Prompt templates: check `prompts/` for the relevant system.txt and user prompts
- Observation diagnostics: `experiments/<branch>/<iteration>/output/<session>/observe_summary.json`
- Default config values: `src/config.py` DEFAULTS dict

### Phase 3: Qualitative session analysis (you are the judge)

For each session, read the baseline and experiment event lists:
- `baselines/<session>/events.json` — human-annotated ground truth
- `experiments/<branch>/<iteration>/output/<session>/events.json` — machine-generated extraction

Perform a qualitative comparison of each session. For every difference between baseline and experiment, classify its severity:

- **noise**: Insignificant timing variations (<1s), minor description wording differences, or extra low-confidence events a human reviewer would ignore.
- **acceptable**: Small timing offsets (1-3s), reasonable type disagreements (e.g. hover vs dwell), or extra events that are plausibly real but not in the baseline.
- **systematic**: Consistent patterns of error across multiple events — e.g. always missing a certain event type, consistently wrong timing, repeated hallucinations of a specific interaction.
- **critical**: Major failures — key user actions (clicks, navigation, text input) completely missing or fabricated, gross timing errors (>5s), or events attributed to the wrong part of the recording.

For each session, report:
- Overall severity rating
- Summary of differences
- List of specific issues with category, severity, description, affected event indices, and examples

### Phase 4: Full-set cross-session evaluation (you are the judge)

After analysing all sessions individually, perform a cross-session evaluation:

1. **Identify systematic patterns** — recurring errors or strengths across 2+ sessions.

2. **Root cause analysis** using the pipeline's architecture:
   - **Observe**: Visual change detection, cursor tracking, moment identification
   - **Analyse**: LLM-based event classification from visual moments
   - **Merge**: Deduplication and final output formatting
   Identify which stage is most likely responsible for each systematic issue.

3. **Score the pipeline** (0-1 scale):
   - **overall_score**: How useful is this pipeline output as-is?
   - **coverage_score**: What fraction of real events does it capture?
   - **type_accuracy_score**: When it finds events, how often is the type correct?
   - **timing_score**: How accurate are the timestamps?

4. **Recommend specific config changes** with confidence scores (0-1).
   - Each recommendation must reference a valid config field path (e.g. `observe.moment_merge_gap_ms`, `analyse.temperature`)
   - Include the current value, recommended value, and rationale
   - Only recommend changes you are confident will improve results

### Phase 5: Write structured output

Write the full evaluation results to `experiments/<branch>/<iteration>/output/`:

1. **`experiment_summary.json`** — update the existing summary with your qualitative and judgment results. The JSON structure follows the `ExperimentSummary` model in `src/experiment_models.py`. Specifically populate:
   - Each session result's `qualitative` field with: `overall_severity`, `summary`, `issues[]` (each with `category`, `severity`, `description`, `affected_events`, `examples`)
   - The top-level `judgment` field with: `overall_score`, `coverage_score`, `type_accuracy_score`, `timing_score`, `systematic_patterns[]`, `root_cause_analysis`, `strengths[]`, `weaknesses[]`, `recommendations[]` (each with `config_key`, `current_value`, `recommended_value`, `rationale`, `confidence`)

2. **`experiment_summary.md`** — regenerate the markdown report incorporating your qualitative analysis and judgment scores.

### Phase 6: Suggest improvements

Present your findings to the user:
- Brief summary of headline metrics per session
- Your qualitative severity ratings and key issues
- Cross-session patterns and root cause analysis
- Pipeline scores
- **Top 3-5 most impactful improvements**, ordered by expected impact, each with:
  - What to change (config, prompt, or pipeline)
  - Why (linked to specific evidence from your analysis)
  - Expected impact
