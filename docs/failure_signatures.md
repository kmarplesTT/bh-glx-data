# Known Failure Signatures

This document lists the known failure signatures/patterns that have been found in the CSV test data

**No Port Connection**:

- Indicator: (`sigdet_time_ms == man_eq_sigdet_timeout*1000`)
- Description: Indicates no port connection as no signal was detected within the alloted time window
- Test Types: PRBS and Data test
- Actions:
  - Run `bh-topology` tool to find out if either of the following exhibited the same behavior on the same run (same timestamp):
    - the connected port (connected via cable if applicable)
    - the port connected to the same QSFP port (if applicable)
  - The group of ports found can be interpretted as a single failure indicating a bad connection
  - Check the test data for the ports in the other test type (PRBS or Data) for similar failures. If they are present, consider it the same failure and note

**0.5 BER Failure**:

- Indicator: BER for any of the Serdes lanes on a port will be approximately 0.5
- Description: Serdes trained successfully and CDR lock achieved but the SerDes lane is unstable
- Test Types: PRBS test only
- Actions:
  - Take note of which lane(s) failed
