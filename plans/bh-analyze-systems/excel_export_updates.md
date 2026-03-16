# Export to Excel Updates

This document outlines a set of requirements for exporting data to excel. The current implementation of the `export-excel` command essentially exports the database into excel format which is not useful. What is useful is having the ability to visualize the output of other various commands in excel format.

Before the plan is implemented, show me the implementation plan

## Current `export-excel` Command

This command is not useful. Remove it and remove any documentation that references (including commends in the code) that you can find.

## New Functionality

The user should be able to export the data from various commands into excel format:

- `stats`: both `table` and `heatmap` formatting options
- `threshold`: both `table` and `heatmap` formatting options
- `training`: both `table` and `heatmap` formatting options
- `custom`: both `table` and `heatmap` formatting options
- `histogram`:
  - Use an Excel statistic chart for the histogram(s)
  - Include the histogram bin legend
- `advanced-stats`
- `info`

### Details

- If the specified excel file does not exist, it should be created
- If the specified excel file exists, a new worksheet should be added to populate the new data
- All applied color-schemes shall be applied to the data in excel; however, cell highlighting should be used to show color rather than the font
