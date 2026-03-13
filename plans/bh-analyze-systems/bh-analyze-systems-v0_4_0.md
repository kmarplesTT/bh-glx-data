# `bh-analyze-systems` Update

This document outlines some desired changes and bug fixes to be done in the next version of `bh-analyze-systems`. The changes are to be carried out by the feature-implementer agent and the user guide is to be updated by the user-guide-writer agent.

Next version : 0.4.0

## Change requests

1. When reporting BER stats, add an extra field for BER values >= 0.1 and do not include them in the Min, Max, Avg calculations. Refer to the new field as" High BER"
2. Change the order of the Min, Max, and Avg columns to [Min, Avg, Max] in the table format
3. Remove the `--exclude-training-failures` from the stats command and simply ignore training failures in all cases
4. For the heatmap case, allow the user to specify which statistics to report in the heatmap: avg, min, or max, high_ber (default to max)
5. Change how the color scheme thresholds are defined. Apply the methodology described in the following example to count and threshold color scheme definitions:
   - The threshold list is currently defined as: `thresholds=[(1e-7, "green"), (1e-6, "yellow"), (5e-6, "bright_yellow"), (1e-5, "red")]`
   - This should mean that:
      - if BER <= 1e-12 : green
      - if 1e-12 < BER <= 1e-7 : yellow
      - if 1e-7 < BER <= 1e-6 : bright_yellow
      - if 1e-6 < BER <= 1e-5 : red
6. Add "orange" between "bright_yellow" and "red" in the pre-defined color schemes in visualization.py
7. Remove old scripts and migration guide entirely

## Bug Fixes

The below list of bug fix request(s) are the result of my interpretation of a feature based on what I am interpreting from the user guide. If the intended functionality of a feature is different from what I am interpreting and there is indeed no bug, then notify me of this so I can determine if I am ok with the functionality as it currently is or if this is indeed a bug and the code and documentation needs to be updated.

1. In the interactive shell, when `stats all --format heatmap` is run, the `table` format is still used
2. Color schemes:
   - If the color scheme thresholds are defined as : `thresholds=[(1e-12, "green"), (1e-7, "yellow"), (1e-6, "bright_yellow"), (1e-5, "red")`,

## Post Implementation Actions

1. Write tests and make sure they pass
2. Update the user guide to reflect changes if necessary
3. Commit the changes and notify me to push them
