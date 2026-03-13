# System Analysis Tool

This document outlines the requirements for a database utility for system analysis. The purpose of the utility is to

- Compile relevant PRBS test data from csv files into a centralized location
- Provide a clean user interface for supporting specific user requests
- Manage the memory usage of large amounts of csv data
- Provide direct user interaction and visualization of the data

Make sure to include:

- The type of structure that should be used to store all relevant PRBS test data
- A mechanism for the user to export the data from the structure into excel format
- User interface definition and supported commands
- Mechanism by which memory space is to be managed for large amounts of csv data

The utility is to provide information to the user and is not to infer any information from the data

You are to define and document an architecture for this utility based on the requirements and information below.

## Data Collection

The utility should collect all csv data from a given location and store it in some parsable structure. During this process:

- Only include test data for which `test_status` is `PASS`, `BER_THRESHOLD_EXCEEDED`, or `TRAINING_FAIL`
- Exclude the following columns in the input csv data from the final structure:
  - Test ID
  - loopback_type
  - max_packet_size_bytes
  - remote_seq_timeout
  - min_packet_words
  - local_seq_update_timeout
  - fec_enable
  - force_rs_272_fec
  - short_channel_eth
  - test_type
  - prbs_pattern
  - prbs_test_total_time
  - prbs_test_check_time
  - board_id
  - pcb_type
  - asic_location
  - train_status
  - reinit_count
  - serdes_train_status
  - macpcs_train_status
  - port_train_status
  - an_speed
  - anlt_retry_cnt
  - man_eq_retry_cnt
  - macpcs_retry_cnt
  - cdr_unlocked_cnt
  - cdr_unlock_transitions
  - training_ber_lane0
  - training_ber_lane1
  - training_ber_lane2
  - training_ber_lane3
  - training_ber_lane4
  - training_ber_lane5
  - training_ber_lane6
  - training_ber_lane7
  - serdes_tx_fir_lane0
  - serdes_tx_fir_lane1
  - serdes_tx_fir_lane2
  - serdes_tx_fir_lane3
  - serdes_tx_fir_lane4
  - serdes_tx_fir_lane5
  - serdes_tx_fir_lane6
  - serdes_tx_fir_lane7
  - aiclk
  - macclk
  - req_lane_error_cnt_hist
  - req_lane_error_cnt_overflow_hist
  - test_pass

## User Requests

The utility should be able to provide the information to the user about a given set of serdes lanes given all PRBS data across all systems:

- For a given set of serdes lanes, show minimum, maximum, and average BER (`acc_ber_lane#`) statistics for each lane
- For a given set of serdes lanes, show the number of `BER_THRESHOLD_EXCEEDED` failures for each lane
  - Represent results as a table of values; or,
  - Represent results as a colorized visualization (e.g., heat map)
- For a given set of serdes lanes, show the number of occurences of `acc_ber_lane#` exceeding a given BER value
  - Represent results as a table of values; or,
  - Represent results as a colorized visualization (e.g., heat map)
- For a given set of serdes lanes, show the number of `TRAINING_FAIL` for each lane
  - Represent results as a table of values; or,
  - Represent results as a colorized visualization (e.g., heat map)

**Notes**:

- The user should be able to request results for a particular `train_speed` or set of `train_speed`s.
- Test data for ports that failed training (i.e., no BER data) should not be included when providing statistics and counts to the user
- When responding to user requests, always include the number of tests and systems tested to provide data context

## Supplemental Information

Refer to @docs/golden_prbs.csv for an example of what the PRBS data looks like for all ports on a single test run for a system
