---
name: run-system-analysis
description: Import and analyze the latest PRBS data from Jira
allowed-tools: "Bash", "Read", "Write", "Edit", "WebFetch",
context: fork
disable-model-invocation: true
argument-hint: true
---

Collect and analyze system data from firmware version $ARGUMENTS

Before starting, activate virtual environment to enable tools: `source .venv/bin/activate`

## Retrieve the data

1. Download the data from Jira: `bh-jira-retrieve --tickets SYS-2826 --output-dir csv_data/`
2. Move the PRBS test data for the latest firmware version (or the firmware version(s) specified in $ARGUMENTS) to `prbs_data/`
3. Clear the old database if it exists: `rm ~/.local/share/bh-glx-data/analysis.db`
4. Build a new database: `bh-analyze-systems ingest ./prbs_data/ --status-filter PASS BER_THRESHOLD_EXCEEDED`
5. Zip the prbs_data folder into `prbs_data_SYS_2826_<firmware_version>_<date>.zip`
6. Delete the unused csv files that were downloaded from Jira

## Generate an excel report

Use the `bh-analyze-systmes` tool to create a report targetting BER of 1e-6 or worse. Put the file in `.claude/skills/run-system-analysis/reports/` with a timestamp in the filename.The objective of the report is to present all information possible to help the reader determine if the high BER is consistent on each system and determine if the high BER is consistent across all systems.

### Guidelines for Reporting

- Make sure to include `info` and heatmap of the `stats` for `all` lanes in the report.
- For `custom` output, use `heatmap` format and always ensure this worksheet immediately follows the `stats all` worksheet
- Include `histogram` and `advanced-stats` for all lanes that have 10 or greater occurrences of BER of 1e-6 or worse
  - The `histogram` and `advanced-stats` worksheets for a particular lane should be grouped together in the worksheet tab bar
- Use the `advanced-stats` to find the hosts on with BER was 1e-6 or worse and include a `plot` for the lane on that system

## Generate lane performance analysis summary

After completing the Excel report, generate a comprehensive lane performance analysis markdown file:

1. Query the database to analyze which lanes perform more poorly than others across all systems
2. Create a markdown report with the same filename as the Excel report but with `.md` extension
3. The analysis should include:
   - Lane distribution of BER issues (percentage breakdown by lane)
   - ETH port performance analysis
   - Critical patterns (e.g., specific bus_id/ETH/lane combinations affecting multiple systems)
   - Systematic vs isolated issues
   - Top problematic combinations by occurrence
   - Conclusions and recommendations for hardware/firmware teams
4. Save the markdown file to `.claude/skills/run-system-analysis/reports/` with matching timestamp to the Excel report
