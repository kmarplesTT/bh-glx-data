#!/usr/bin/env python3
"""
Extract test data CSV files from Quanta test archives

This tool:
1. Takes a QC3_UBB_*.tar.gz archive as input
2. Extracts data_test_*.csv and prbs_test_*.csv files from nested archives
3. Stores the extracted CSV files in the quanta/ directory

File Organization:
- QC2/QC3 test archive (*.tar.gz) contains:
  - tt_funtest_ubb_*/
    - ft_eth_stress_*.tar.gz or ft_burnin_*.tar.gz contains:
      - ft_eth_stress/ or ft_burnin/
        - data_test_*.csv
        - prbs_test_*.csv
"""

import sys
import tarfile
import tempfile
import shutil
from pathlib import Path


def extract_csv_files(archive_path: Path, output_dir: Path, archive_basename: str = None) -> int:
    """
    Extract data_test_*.csv and prbs_test_*.csv files from a QC2/QC3 test archive.

    Handles nested tar.gz structure:
    - Opens the test archive (QC2-FRO-*, QC2-FAT-*, QC3_UBB_*, etc.)
    - Extracts tt_funtest_ubb_*/ft_eth_stress_*.tar.gz or tt_funtest_ubb_*/ft_burnin_*.tar.gz
    - Extracts data_test_*.csv and prbs_test_*.csv from ft_eth_stress/ or ft_burnin/ directories

    Args:
        archive_path: Path to the test archive file
        output_dir: Destination directory for extracted CSV files
        archive_basename: Optional basename to use for output filenames (defaults to archive stem)

    Returns:
        Number of CSV files extracted
    """
    csv_count = 0

    # Use archive stem as basename if not provided
    if archive_basename is None:
        archive_basename = archive_path.stem.replace('.tar', '')

    print(f"Processing {archive_path.name}...")

    # Create temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        try:
            # Extract the UBB archive
            with tarfile.open(archive_path, 'r:gz') as tar:
                # Find tt_funtest_ubb_* directories containing ft_eth_stress_*.tar.gz or ft_burnin_*.tar.gz
                funtest_members = [m for m in tar.getmembers()
                                  if 'tt_funtest_ubb_' in m.name and
                                  ('ft_eth_stress_' in m.name or 'ft_burnin_' in m.name) and
                                  m.name.endswith('.tar.gz')]

                if not funtest_members:
                    print(f"  Warning: No ft_eth_stress_*.tar.gz or ft_burnin_*.tar.gz found in archive")
                    return 0

                # Extract the test archives (ft_eth_stress or ft_burnin)
                for member in funtest_members:
                    tar.extract(member, temp_path)
                    test_archive = temp_path / member.name

                    # Extract CSV files from test archive
                    with tarfile.open(test_archive, 'r:gz') as test_tar:
                        # Look for CSV files in ft_eth_stress/ or ft_burnin/ directories
                        csv_members = [m for m in test_tar.getmembers()
                                      if (m.name.startswith('ft_eth_stress/') or m.name.startswith('ft_burnin/')) and
                                      (('data_test_' in m.name and m.name.endswith('.csv')) or
                                       ('prbs_test_' in m.name and m.name.endswith('.csv')))]

                        if not csv_members:
                            print(f"  Warning: No CSV files found in {member.name}")
                            continue

                        for csv_member in csv_members:
                            # Extract to output directory with a unique name
                            csv_filename = Path(csv_member.name).name
                            # Prefix with the archive basename to avoid collisions
                            output_filename = f"{archive_basename}_{csv_filename}"
                            output_path = output_dir / output_filename

                            # Extract the file
                            test_tar.extract(csv_member, temp_path)
                            extracted_file = temp_path / csv_member.name

                            # Copy to output directory
                            shutil.copy2(extracted_file, output_path)
                            print(f"  Extracted: {output_filename}")
                            csv_count += 1

        except (tarfile.TarError, OSError) as e:
            print(f"  Error extracting from {archive_path.name}: {e}", file=sys.stderr)
            return 0

    return csv_count


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Extract test CSV files from Quanta QC2/QC3 test archives',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract CSV files from a test archive
  %(prog)s QC2-FRO-QTWS7TKC260700003-0.tar.gz

  # Specify custom output directory
  %(prog)s QC2-FRO-QTWS7TKC260700003-0.tar.gz --output-dir my_data/

  # Specify custom output filename prefix
  %(prog)s QC2-FRO-QTWS7TKC260700003-0.tar.gz --prefix D2K-95

The tool will:
  1. Open the test archive
  2. Find and extract ft_eth_stress_*.tar.gz or ft_burnin_*.tar.gz archives
  3. Extract data_test_*.csv and prbs_test_*.csv files to quanta/ directory
"""
    )

    parser.add_argument(
        'archive_file',
        type=str,
        help='Path to the QC2/QC3 test archive file (e.g., QC2-FRO-*.tar.gz)'
    )

    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='quanta',
        help='Output directory for extracted CSV files (default: quanta/)'
    )

    parser.add_argument(
        '-p', '--prefix',
        type=str,
        default=None,
        help='Prefix for output filenames (default: archive basename)'
    )

    args = parser.parse_args()

    # Validate input file
    archive_path = Path(args.archive_file)
    if not archive_path.exists():
        print(f"Error: File not found: {archive_path}", file=sys.stderr)
        sys.exit(1)

    if not archive_path.name.endswith('.tar.gz'):
        print(f"Error: Expected a .tar.gz file, got: {archive_path.name}", file=sys.stderr)
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir.absolute()}")

    # Extract CSV files
    print()
    csv_count = extract_csv_files(archive_path, output_dir, args.prefix)

    print(f"\n{'='*80}")
    print(f"Extraction complete!")
    print(f"Total CSV files extracted: {csv_count}")
    print(f"Output directory: {output_dir.absolute()}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
