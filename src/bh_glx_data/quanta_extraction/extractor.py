"""CSV extraction logic from Quanta test archives."""

import logging
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import List

from bh_glx_data.core.exceptions import DataProcessingError
from bh_glx_data.core.models import ExtractionResult

logger = logging.getLogger(__name__)


def extract_csv_from_archive(
    archive_path: Path,
    output_dir: Path,
    archive_basename: str = None,
) -> ExtractionResult:
    """Extract data_test_*.csv and prbs_test_*.csv files from a QC2/QC3 test archive.

    Handles nested tar.gz structure:
    - Opens the test archive (QC2-FRO-*, QC2-FAT-*, QC3_UBB_*, etc.)
    - Extracts tt_funtest_ubb_*/ft_eth_stress_*.tar.gz or tt_funtest_ubb_*/ft_burnin_*.tar.gz
    - Extracts data_test_*.csv and prbs_test_*.csv from ft_eth_stress/ or ft_burnin/ directories

    Args:
        archive_path: Path to the test archive file
        output_dir: Destination directory for extracted CSV files
        archive_basename: Optional basename to use for output filenames (defaults to archive stem)

    Returns:
        ExtractionResult with summary of extraction

    Raises:
        DataProcessingError: If archive processing fails
    """
    # Validate archive exists
    if not archive_path.exists():
        raise DataProcessingError(f"Archive file not found: {archive_path}")

    if not archive_path.name.endswith(".tar.gz"):
        raise DataProcessingError(f"Expected a .tar.gz file, got: {archive_path.name}")

    # Use archive stem as basename if not provided
    if archive_basename is None:
        archive_basename = archive_path.stem.replace(".tar", "")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Processing {archive_path.name}...")

    extracted_files: List[Path] = []
    failed_serials: List[str] = []
    errors: List[str] = []

    # Create temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        try:
            # Extract the UBB archive
            with tarfile.open(archive_path, "r:gz") as tar:
                # Find tt_funtest_ubb_* directories containing ft_eth_stress_*.tar.gz or ft_burnin_*.tar.gz
                funtest_members = [
                    m
                    for m in tar.getmembers()
                    if "tt_funtest_ubb_" in m.name
                    and ("ft_eth_stress_" in m.name or "ft_burnin_" in m.name)
                    and m.name.endswith(".tar.gz")
                ]

                if not funtest_members:
                    error_msg = "No ft_eth_stress_*.tar.gz or ft_burnin_*.tar.gz found in archive"
                    logger.warning(f"  {error_msg}")
                    return ExtractionResult(
                        extracted_files=[],
                        failed_serials=[],
                        total_files=0,
                        success=False,
                        error_message=error_msg,
                    )

                # Extract the test archives (ft_eth_stress or ft_burnin)
                for member in funtest_members:
                    try:
                        tar.extract(member, temp_path)
                        test_archive = temp_path / member.name

                        # Extract CSV files from test archive
                        with tarfile.open(test_archive, "r:gz") as test_tar:
                            # Look for CSV files in ft_eth_stress/ or ft_burnin/ directories
                            csv_members = [
                                m
                                for m in test_tar.getmembers()
                                if (
                                    m.name.startswith("ft_eth_stress/")
                                    or m.name.startswith("ft_burnin/")
                                )
                                and (
                                    ("data_test_" in m.name and m.name.endswith(".csv"))
                                    or ("prbs_test_" in m.name and m.name.endswith(".csv"))
                                )
                            ]

                            if not csv_members:
                                warning = f"No CSV files found in {member.name}"
                                logger.warning(f"  {warning}")
                                errors.append(warning)
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
                                logger.info(f"  Extracted: {output_filename}")
                                extracted_files.append(output_path)

                    except Exception as e:
                        error_msg = f"Error extracting from {member.name}: {e}"
                        logger.error(f"  {error_msg}")
                        errors.append(error_msg)
                        continue

        except tarfile.TarError as e:
            raise DataProcessingError(f"Error reading archive {archive_path.name}: {e}")
        except OSError as e:
            raise DataProcessingError(f"OS error processing archive {archive_path.name}: {e}")

    total_files = len(extracted_files)
    success = total_files > 0
    error_message = "; ".join(errors) if errors else None

    return ExtractionResult(
        extracted_files=extracted_files,
        failed_serials=failed_serials,
        total_files=total_files,
        success=success,
        error_message=error_message,
    )


def extract_from_multiple_archives(
    archive_paths: List[Path],
    output_dir: Path,
) -> ExtractionResult:
    """Extract CSV files from multiple archives.

    Args:
        archive_paths: List of archive file paths
        output_dir: Output directory for extracted files

    Returns:
        Combined ExtractionResult for all archives
    """
    all_extracted_files: List[Path] = []
    all_failed_serials: List[str] = []
    all_errors: List[str] = []

    for archive_path in archive_paths:
        try:
            result = extract_csv_from_archive(archive_path, output_dir)
            all_extracted_files.extend(result.extracted_files)
            all_failed_serials.extend(result.failed_serials)
            if result.error_message:
                all_errors.append(f"{archive_path.name}: {result.error_message}")
        except DataProcessingError as e:
            logger.error(f"Failed to process {archive_path.name}: {e}")
            all_errors.append(f"{archive_path.name}: {e}")

    total_files = len(all_extracted_files)
    success = total_files > 0
    error_message = "; ".join(all_errors) if all_errors else None

    return ExtractionResult(
        extracted_files=all_extracted_files,
        failed_serials=all_failed_serials,
        total_files=total_files,
        success=success,
        error_message=error_message,
    )
