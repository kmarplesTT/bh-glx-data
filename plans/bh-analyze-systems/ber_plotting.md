# BER Plotting Feature

This document describes the requirements for a new feature in the `bh-analyze-systems` tool. This feature will allow the user to plot the BER values for a given serdes lane over time.

## Requirements

The specific requirements for this feature are as follows:

1. The plot is to be represented in the command line as a table of timestamps and BER values
2. The `--excel-output` argument shall be supported in which case an excel chart will be generated
3. When generating an excel output, as with the other commands that support the `--excel-output` option:
   - If the given `.xlsx` filename provided does not exist, create it and add a new worksheet with the plot
   - If the given `.xlsx` filename provided exists, add a new worksheet with the same naming format used for `advanced-stats`
4. Lane selection provided by the user must include: system name, bus_id, and eth_id. Lane number is optional
   - In the case where lane number is not provided, plots will be generated for all lanes for the eth_id
   - In the case where lane number is provided, a single plot will be generated for that lane
5. The "Date" for each entry in the database shall represent the x-axis and be used to indicate the order of the plotted data
   - The data points should be spaced equally on the plot regardless of the time between data points

## Other Actions

1. Generate tests for this new feature
2. Run the tests and fix any bugs necessary
3. Provide a short list of commands for me to test various cases and view the excel output myself
