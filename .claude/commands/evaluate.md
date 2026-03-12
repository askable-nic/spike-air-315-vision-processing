Run evaluation(s) and suggest improvements to the VEX pipeline.

## Arguments

$ARGUMENTS — One or more `branch/iteration` pairs (e.g. `visual-change-driven/1`), optionally followed by session IDs. If no arguments, evaluate the most recent experiment iteration.

## Instructions

1. **Parse arguments** to determine which branch/iteration(s) and optional session(s) to evaluate.
   - If no arguments given, look at `experiments/` to find the most recent branch/iteration with output.
   - If a session is specified, pass `-s <session>` to each evaluation.

2. **Run evaluations** using the `vex evaluate` CLI with `--verbose` flag:
   ```
   vex evaluate -b <branch> -i <iteration> -v [-s <session>]
   ```
   Run multiple evaluations sequentially if multiple branch/iteration pairs are given.

3. **Read supporting context** to inform your suggestions. In parallel:
   - Read the experiment config if it exists: `experiments/<branch>/<iteration>/config.yaml` and `experiments/<branch>/config.yaml`
   - Read the prompts used: check `prompts/` directory for the relevant prompt templates (system.txt, and whichever user prompt the branch uses)
   - Read `experiments/<branch>/<iteration>/output/<session>/observe_summary.json` for observation-stage diagnostics
   - Read `src/config.py` DEFAULTS to understand what config values were used (if no override YAML exists)

4. **Analyse the results** focusing on:
   - **Recall gaps**: Which baseline event types are being missed entirely? Why might the pipeline fail to detect them?
   - **Precision issues**: What false positives is the experiment producing? Are they plausible events the baseline missed, or genuine errors?
   - **Type confusion**: Are events being classified as the wrong type (e.g. `change_ui_state` when it should be `click`)?
   - **Timing accuracy**: How far off are the matched event timestamps? Are there systematic biases?
   - **Description quality**: For matched pairs, how well do experiment descriptions capture what the baseline describes?
   - **Coverage patterns**: Are there temporal regions of the session that are well-covered vs poorly-covered?

5. **Suggest concrete improvements** in these categories:
   - **Prompt changes**: Specific wording changes to system.txt or user prompts that could help with missed event types or type confusion
   - **Config tuning**: Specific parameter changes (with values) that could improve detection - reference the parameter names from `src/config.py`
   - **Pipeline changes**: Structural improvements to observation, analysis, or merge stages
   - **Baseline gaps**: Cases where the experiment found plausible events the baseline missed (these aren't real errors)

6. **Format your response** as:
   - Brief summary of each evaluation's headline metrics
   - Top 3-5 most impactful issues found
   - Ordered list of suggested improvements, each with: what to change, why, and expected impact
