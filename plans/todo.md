# TODO

These items potential can be addressed at a later date:

- Look into adding option to generate PDF report of stats or exporting to excel or something
- Look into expanding the functionality of the export-to-excel feature
- When exporting database to excel if the number of rows exceeds the max values supported by excel (1048576), start a new page to continue exporting the data into
- Fix the failing system_analysis tests
- In the stats command the --statistic remove the existing avg command and change the name of the variance option to avg
- Add query feature to dump data (e.g., BER) data for a particular system, bus_id, eth id, serdes lane
  - an example use-case would be if I see min/max/avg BER stats for a lane and I suspect they are being calculated incorrectly
