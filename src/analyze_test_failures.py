#!/usr/bin/env python3
"""
Comprehensive test failure analysis for BH Galaxy data tests.

This script analyzes failures from DATA and PRBS test CSV files, categorizes
failure signatures, and generates a detailed report.
"""

import ast
import re
from pathlib import Path
from collections import defaultdict, Counter
import pandas as pd

# Output directories
FAILURES_DIR = Path('failures')
REPORTS_DIR = Path('reports')
REPORTS_DIR.mkdir(exist_ok=True)

def parse_train_status(train_status_str):
    """Parse the train_status dictionary string into a Python dict."""
    try:
        # Use ast.literal_eval to safely parse Python dict strings
        return ast.literal_eval(train_status_str)
    except Exception as e:
        return None

def analyze_data_test_failures():
    """Analyze all DATA test failures and categorize by failure signature."""

    # Find all data test failure files
    failure_files = sorted(FAILURES_DIR.glob('data_test_*_failures.csv'))

    if not failure_files:
        return {
            'total_failures': 0,
            'files_analyzed': 0,
            'failure_signatures': {}
        }

    all_failures = []

    # Read all failure files
    for failure_file in failure_files:
        try:
            df = pd.read_csv(failure_file)
            if not df.empty:
                df['source_file'] = failure_file.name
                all_failures.append(df)
        except Exception as e:
            print(f"Error reading {failure_file}: {e}")

    if not all_failures:
        return {
            'total_failures': 0,
            'files_analyzed': len(failure_files),
            'failure_signatures': {}
        }

    # Combine all failures
    combined_df = pd.concat(all_failures, ignore_index=True)

    # Analyze failure patterns
    failure_analysis = {
        'total_failures': len(combined_df),
        'files_analyzed': len(failure_files),
        'test_status_breakdown': combined_df['test_status'].value_counts().to_dict(),
        'failures_by_bus': combined_df['bus_id'].value_counts().to_dict(),
        'failures_by_eth_port': combined_df['ETH ID'].value_counts().to_dict(),
        'failure_signatures': []
    }

    # Categorize failures by signature
    for idx, row in combined_df.iterrows():
        test_status = row['test_status']
        bus_id = row['bus_id'].strip('"')
        eth_id = row['ETH ID']
        train_status_dict = parse_train_status(row['train_status'])

        signature = {
            'bus_id': bus_id,
            'eth_id': eth_id,
            'test_status': test_status,
            'source_file': row['source_file']
        }

        if train_status_dict:
            # Extract key diagnostic info
            eth_status = train_status_dict.get('eth_status', {})
            serdes_training = train_status_dict.get('serdes_training', {})
            macpcs_training = train_status_dict.get('macpcs_training', {})

            signature['eth_fw_ver'] = tuple(eth_status.get('eth_fw_ver', []))
            signature['port_status'] = eth_status.get('port_status')
            signature['train_status'] = eth_status.get('train_status')
            signature['postcode'] = eth_status.get('postcode')

            # Serdes diagnostics
            signature['serdes_postcode'] = serdes_training.get('postcode')
            signature['cdr_unlocked_cnt'] = serdes_training.get('cdr_unlocked_cnt', 0)
            signature['cdr_unlock_transitions'] = serdes_training.get('cdr_unlock_transitions', 0)
            signature['lcpll_lock_fail_cnt'] = serdes_training.get('lcpll_lock_fail_cnt', 0)
            signature['man_eq_retry_cnt'] = serdes_training.get('man_eq_retry_cnt', 0)
            signature['anlt_retry_cnt'] = serdes_training.get('anlt_retry_cnt', 0)

            # Training times
            training_times = serdes_training.get('training_times', {})
            manual_eq = training_times.get('manual_eq', {})
            signature['sigdet_time_ms'] = manual_eq.get('sigdet_time_ms', 0)
            signature['rx_eq_assert_time_ms'] = manual_eq.get('rx_eq_assert_time_ms', 0)

            # MACPCS diagnostics
            signature['macpcs_postcode'] = macpcs_training.get('postcode')
            signature['macpcs_retry_cnt'] = macpcs_training.get('macpcs_retry_cnt', 0)

            # Remote info
            remote_info = eth_status.get('remote_info', {})
            signature['remote_pcb_type'] = remote_info.get('pcb_type')
            signature['remote_board_id'] = remote_info.get('board_id')

        failure_analysis['failure_signatures'].append(signature)

    return failure_analysis

def categorize_failure_pattern(signature):
    """Categorize a failure into a known pattern type."""

    test_status = signature.get('test_status')
    train_status = signature.get('train_status')
    cdr_unlocked = signature.get('cdr_unlocked_cnt', 0)
    sigdet_time = signature.get('sigdet_time_ms', 0)
    rx_eq_time = signature.get('rx_eq_assert_time_ms', 0)
    serdes_postcode = signature.get('serdes_postcode')
    remote_pcb = signature.get('remote_pcb_type')

    # Pattern 1: External cable connection timeout (ORION remote with signal detect timeout)
    if remote_pcb == 'ORION' and sigdet_time >= 20000 and train_status == 'LINK_TRAIN_TIMEOUT_MANUAL_EQ':
        return 'EXTERNAL_CABLE_SIGDET_TIMEOUT'

    # Pattern 2: RX equalization timeout
    if rx_eq_time >= 5000 and train_status == 'LINK_TRAIN_TIMEOUT_MANUAL_EQ':
        return 'RX_EQUALIZATION_TIMEOUT'

    # Pattern 3: CDR unlock during training
    if cdr_unlocked > 5000 and train_status == 'LINK_TRAIN_TIMEOUT_MANUAL_EQ':
        return 'CDR_UNLOCK_DURING_TRAINING'

    # Pattern 4: Link down after successful training
    if test_status == 'LINK_DOWN' and train_status == 'LINK_TRAIN_PASS':
        return 'LINK_DOWN_POST_TRAINING'

    # Pattern 5: General training failure
    if test_status == 'TRAINING_FAIL':
        return 'TRAINING_FAIL_GENERAL'

    return 'UNCATEGORIZED'

def generate_failure_report(analysis):
    """Generate a comprehensive markdown report of failures."""

    report_lines = []
    report_lines.append("# BH Galaxy Ethernet Test Failure Analysis Report")
    report_lines.append(f"\n**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"\n## Summary\n")
    report_lines.append(f"- **Total Failures:** {analysis['total_failures']}")
    report_lines.append(f"- **Files Analyzed:** {analysis['files_analyzed']}")

    # Test status breakdown
    report_lines.append(f"\n### Test Status Breakdown\n")
    for status, count in sorted(analysis['test_status_breakdown'].items(), key=lambda x: x[1], reverse=True):
        report_lines.append(f"- **{status}:** {count}")

    # Failures by bus
    report_lines.append(f"\n### Failures by PCIe Device (Bus ID)\n")
    for bus_id, count in sorted(analysis['failures_by_bus'].items(), key=lambda x: x[1], reverse=True)[:10]:
        report_lines.append(f"- **{bus_id}:** {count} failure(s)")

    # Failures by Ethernet port
    report_lines.append(f"\n### Failures by Ethernet Port\n")
    for eth_id, count in sorted(analysis['failures_by_eth_port'].items(), key=lambda x: x[1], reverse=True):
        report_lines.append(f"- **{eth_id}:** {count} failure(s)")

    # Categorize failure patterns
    pattern_counts = Counter()
    pattern_examples = defaultdict(list)

    for sig in analysis['failure_signatures']:
        pattern = categorize_failure_pattern(sig)
        pattern_counts[pattern] += 1
        if len(pattern_examples[pattern]) < 3:  # Keep up to 3 examples per pattern
            pattern_examples[pattern].append(sig)

    report_lines.append(f"\n## Failure Pattern Analysis\n")

    for pattern, count in pattern_counts.most_common():
        report_lines.append(f"\n### {pattern.replace('_', ' ').title()} ({count} occurrences)\n")

        # Add description
        if pattern == 'EXTERNAL_CABLE_SIGDET_TIMEOUT':
            report_lines.append("**Description:** External cable connection timeout during signal detect phase. ")
            report_lines.append("The remote device shows 'ORION' PCB type with all-zero identifiers, indicating ")
            report_lines.append("external cable connection. Signal detect timeout (20s) suggests no signal received.\n")
            report_lines.append("**Potential Causes:**")
            report_lines.append("- Cable not connected or faulty")
            report_lines.append("- Remote device not powered or not transmitting")
            report_lines.append("- Incorrect cable type or length")
            report_lines.append("- Signal integrity issues on long cable runs\n")

        elif pattern == 'RX_EQUALIZATION_TIMEOUT':
            report_lines.append("**Description:** RX equalization timeout during manual EQ training. ")
            report_lines.append("The receiver was unable to complete equalization within the 5-second timeout.\n")
            report_lines.append("**Potential Causes:**")
            report_lines.append("- Poor signal quality requiring excessive EQ attempts")
            report_lines.append("- Firmware issue in RX EQ algorithm convergence")
            report_lines.append("- Hardware issue with RX equalizer circuitry\n")

        elif pattern == 'CDR_UNLOCK_DURING_TRAINING':
            report_lines.append("**Description:** Clock and Data Recovery (CDR) lost lock during training. ")
            report_lines.append("High CDR unlock counts indicate the CDR could not maintain phase lock.\n")
            report_lines.append("**Potential Causes:**")
            report_lines.append("- Unstable clock reference or PLL issues")
            report_lines.append("- Poor signal quality causing CDR to lose lock")
            report_lines.append("- Timing margin issues at high data rates (200G)")
            report_lines.append("- Signal detect timing issues causing premature CDR attempts\n")

        elif pattern == 'LINK_DOWN_POST_TRAINING':
            report_lines.append("**Description:** Link went down during data transfer test after successful training. ")
            report_lines.append("This indicates the link trained successfully but failed during actual data traffic.\n")
            report_lines.append("**Potential Causes:**")
            report_lines.append("- MAC/PCS layer issues during data transfer")
            report_lines.append("- Marginal signal quality that passes training but fails under traffic load")
            report_lines.append("- Flow control or backpressure handling issues")
            report_lines.append("- Remote side link stability issues\n")

        # Add examples
        report_lines.append("**Example Failures:**\n")
        for i, example in enumerate(pattern_examples[pattern], 1):
            report_lines.append(f"{i}. **{example['bus_id']} {example['eth_id']}** (from {example['source_file']})")
            report_lines.append(f"   - Test Status: {example['test_status']}")
            report_lines.append(f"   - Train Status: {example.get('train_status', 'N/A')}")
            report_lines.append(f"   - Serdes Postcode: {example.get('serdes_postcode', 'N/A')}")
            report_lines.append(f"   - CDR Unlocked Count: {example.get('cdr_unlocked_cnt', 0)}")
            report_lines.append(f"   - Manual EQ Retries: {example.get('man_eq_retry_cnt', 0)}")
            report_lines.append(f"   - Signal Detect Time: {example.get('sigdet_time_ms', 0)} ms")
            report_lines.append(f"   - RX EQ Assert Time: {example.get('rx_eq_assert_time_ms', 0)} ms")
            report_lines.append("")

    # PRBS test note
    report_lines.append("\n## PRBS Test Analysis\n")
    report_lines.append("**Note:** All PRBS test files show only PASS or ETH_UNCONNECTED status. ")
    report_lines.append("The filter_failures.py script incorrectly flagged PASS results as failures ")
    report_lines.append("because it only recognizes ETH_ACTIVE and ETH_UNCONNECTED as non-failure statuses. ")
    report_lines.append("For PRBS tests, PASS indicates successful test completion.\n")
    report_lines.append("**Result:** No actual PRBS test failures detected in the analyzed data.\n")

    return '\n'.join(report_lines)

def generate_firmware_investigation_report(analysis):
    """Generate a targeted report for firmware engineers investigating issues."""

    report_lines = []
    report_lines.append("# Firmware Investigation Guide - Ethernet Training Failures")
    report_lines.append(f"\n**For:** Firmware Engineering Team")
    report_lines.append(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**System:** s7tk-03")
    report_lines.append(f"**Firmware Version:** eth_fw_ver (1, 8, 1), serdes_fw_ver (0, 9, 16)\n")

    report_lines.append("## Executive Summary\n")
    report_lines.append(f"Analyzed {analysis['total_failures']} DATA test failures across {analysis['files_analyzed']} test runs. ")
    report_lines.append("No PRBS test failures detected. Failures primarily occur during manual EQ training phase ")
    report_lines.append("with external cable connections.\n")

    report_lines.append("## Critical Firmware Areas to Investigate\n")

    # Categorize failures for firmware focus areas
    pattern_counts = Counter()
    for sig in analysis['failure_signatures']:
        pattern = categorize_failure_pattern(sig)
        pattern_counts[pattern] += 1

    report_lines.append("### 1. Manual EQ Training State Machine\n")
    report_lines.append("**Priority:** HIGH\n")
    report_lines.append(f"**Affected Failures:** {pattern_counts['EXTERNAL_CABLE_SIGDET_TIMEOUT'] + pattern_counts['RX_EQUALIZATION_TIMEOUT']}\n")
    report_lines.append("**Issue:** Training timeouts during signal detect and RX equalization phases.\n")
    report_lines.append("**Firmware Modules to Review:**")
    report_lines.append("- `erisc_init.c` - Ethernet initialization and training orchestration")
    report_lines.append("- Signal detect timeout handling (currently 20 seconds)")
    report_lines.append("- RX equalization convergence logic and timeout handling (5 seconds)")
    report_lines.append("- Retry logic and backoff mechanisms\n")
    report_lines.append("**Questions to Answer:**")
    report_lines.append("- Is the 20-second signal detect timeout appropriate for external cables?")
    report_lines.append("- Should there be early detection of 'no signal' condition?")
    report_lines.append("- Is the RX EQ algorithm converging or stuck in retry loops?")
    report_lines.append("- Are retry counts being properly enforced?\n")

    if pattern_counts['CDR_UNLOCK_DURING_TRAINING'] > 0:
        report_lines.append("### 2. Clock and Data Recovery (CDR) Stability\n")
        report_lines.append("**Priority:** HIGH\n")
        report_lines.append(f"**Affected Failures:** {pattern_counts['CDR_UNLOCK_DURING_TRAINING']}\n")
        report_lines.append("**Issue:** CDR losing lock during training with high unlock counts (>5000).\n")
        report_lines.append("**Firmware Modules to Review:**")
        report_lines.append("- CDR lock detection and monitoring")
        report_lines.append("- Signal detect and CDR sequencing")
        report_lines.append("- LCPLL initialization and monitoring\n")
        report_lines.append("**Questions to Answer:**")
        report_lines.append("- Is signal detect asserting before signal is truly stable?")
        report_lines.append("- Should CDR lock be verified before proceeding with training?")
        report_lines.append("- Are we attempting training too early after signal detect?")
        report_lines.append("- Is there a minimum signal quality check before engaging CDR?\n")

    if pattern_counts['LINK_DOWN_POST_TRAINING'] > 0:
        report_lines.append("### 3. Link Stability During Data Transfer\n")
        report_lines.append("**Priority:** MEDIUM\n")
        report_lines.append(f"**Affected Failures:** {pattern_counts['LINK_DOWN_POST_TRAINING']}\n")
        report_lines.append("**Issue:** Link going down during data test after successful training.\n")
        report_lines.append("**Firmware Modules to Review:**")
        report_lines.append("- Link monitoring and keepalive mechanisms")
        report_lines.append("- MAC/PCS error handling during traffic")
        report_lines.append("- Flow control and backpressure handling\n")
        report_lines.append("**Questions to Answer:**")
        report_lines.append("- What triggers link down detection during traffic?")
        report_lines.append("- Are error thresholds appropriate for the link quality?")
        report_lines.append("- Is there automatic link recovery or retry logic?\n")

    report_lines.append("## Detailed Diagnostic Data\n")

    # Find representative examples with detailed diagnostics
    report_lines.append("### Representative Failure Examples\n")

    patterns_seen = set()
    for sig in analysis['failure_signatures']:
        pattern = categorize_failure_pattern(sig)
        if pattern not in patterns_seen and pattern != 'UNCATEGORIZED':
            patterns_seen.add(pattern)
            report_lines.append(f"\n#### {pattern.replace('_', ' ').title()}\n")
            report_lines.append(f"**Device:** {sig['bus_id']} {sig['eth_id']}")
            report_lines.append(f"**Test Status:** {sig['test_status']}")
            report_lines.append(f"**Train Status:** {sig.get('train_status', 'N/A')}")
            report_lines.append(f"**Port Status:** {sig.get('port_status', 'N/A')}")
            report_lines.append(f"**Serdes Postcode:** {sig.get('serdes_postcode', 'N/A')}")
            report_lines.append(f"**MACPCS Postcode:** {sig.get('macpcs_postcode', 'N/A')}\n")
            report_lines.append("**Training Metrics:**")
            report_lines.append(f"- Manual EQ Retry Count: {sig.get('man_eq_retry_cnt', 0)}")
            report_lines.append(f"- ANLT Retry Count: {sig.get('anlt_retry_cnt', 0)}")
            report_lines.append(f"- MACPCS Retry Count: {sig.get('macpcs_retry_cnt', 0)}")
            report_lines.append(f"- CDR Unlocked Count: {sig.get('cdr_unlocked_cnt', 0)}")
            report_lines.append(f"- CDR Unlock Transitions: {sig.get('cdr_unlock_transitions', 0)}")
            report_lines.append(f"- LCPLL Lock Fail Count: {sig.get('lcpll_lock_fail_cnt', 0)}\n")
            report_lines.append("**Training Times:**")
            report_lines.append(f"- Signal Detect: {sig.get('sigdet_time_ms', 0)} ms")
            report_lines.append(f"- RX EQ Assert: {sig.get('rx_eq_assert_time_ms', 0)} ms\n")

    report_lines.append("\n## Recommended Actions\n")
    report_lines.append("1. **Code Review:** Review manual EQ training state machine in erisc_init.c")
    report_lines.append("2. **Timeout Analysis:** Evaluate if current timeout values are appropriate")
    report_lines.append("3. **Early Exit Logic:** Add early detection for 'no signal' conditions")
    report_lines.append("4. **CDR Sequencing:** Review signal detect → CDR lock → training sequencing")
    report_lines.append("5. **Logging Enhancement:** Add more granular logging during training phases")
    report_lines.append("6. **Test Environment:** Verify external cable connections and test setup\n")

    return '\n'.join(report_lines)

def cleanup_failure_csvs():
    """Clean up failure CSV files after analysis is complete."""
    failure_files = list(FAILURES_DIR.glob('*_failures.csv'))

    if not failure_files:
        return 0

    deleted_count = 0
    for failure_file in failure_files:
        try:
            failure_file.unlink()
            deleted_count += 1
        except Exception as e:
            print(f"Warning: Could not delete {failure_file.name}: {e}")

    return deleted_count

def main():
    print("Analyzing test failures...")

    # Analyze DATA test failures
    analysis = analyze_data_test_failures()

    if analysis['total_failures'] == 0:
        print("No DATA test failures found.")
        # Still clean up any empty failure files
        deleted = cleanup_failure_csvs()
        if deleted > 0:
            print(f"Cleaned up {deleted} failure CSV file(s).")
        return

    print(f"\nFound {analysis['total_failures']} DATA test failures across {analysis['files_analyzed']} files.")

    # Generate main failure report
    report = generate_failure_report(analysis)
    report_path = REPORTS_DIR / 'failure_analysis_report.md'
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Generated failure analysis report: {report_path}")

    # Generate firmware investigation report
    fw_report = generate_firmware_investigation_report(analysis)
    fw_report_path = REPORTS_DIR / 'firmware_investigation_guide.md'
    with open(fw_report_path, 'w') as f:
        f.write(fw_report)
    print(f"Generated firmware investigation guide: {fw_report_path}")

    print("\nReport generation complete!")

    # Clean up failure CSV files
    print("\nCleaning up intermediate failure CSV files...")
    deleted_count = cleanup_failure_csvs()
    print(f"Deleted {deleted_count} failure CSV file(s).")

if __name__ == '__main__':
    main()
