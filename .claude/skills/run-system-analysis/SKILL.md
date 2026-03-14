---
name: run-system-analysis
description: Import and analyze the latest PRBS data from Jira
allowed-tools: "Bash", "Read", "Write", "Edit", "WebFetch",
context: fork
disable-model-invocation: true
argument-hint: true
---

Collect and analyze system data from firmware version $ARGUMENTS

Activate virtual environment to enable tools: `source .venv/bin/activate`

1. Download the data from Jira: `bh-jira-retrieve --tickets SYS-2826 --output-dir csv_data/`
2. Move the PRBS test data for the latest firmware version (or the firmware version(s) specified in $ARGUMENTS) to `prbs_data/`
3. Clear the old database if it exists: `rm ~/.local/share/bh-glx-data/analysis.db`
4. Build a new database: `bh-analyze-systems ingest ./prbs_data/ --status-filter PASS BER_THRESHOLD_EXCEEDED`
5. Zip the prbs_data folder into `prbs_data_SYS_2826_<firmware_version>_<date>.zip`
6. Delete the unused csv files that were downloaded from Jira
7. Summarize the info: `bh-analyze-systems info`
8. Gather data on lanes that tend to perform poorly: `bh-analyze-systems custom all 1e-6 --format table`
9. From the output of the previous command, if any standout gather that `max` and `variance` stats for those lanes
   - For example,

   ```bash
   bh-analyze-systems stats <system(s)> --statistic max
   bh-analyze-systems stats <system(s)> --statistic variance
   ```

   - Do this for all ports that stand out

Generate a summary of important information from this process and store it in: `.claude/skilss/run-system-analysis/logs/`.
