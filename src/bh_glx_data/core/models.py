"""Data models for BH Galaxy Data Analysis Tool.

This module defines dataclasses for representing test results, failures,
configurations, and hardware metadata.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class TestType(Enum):
    """Test type enumeration."""

    SERDES_PRBS = "SERDES_PRBS"
    SIMPLE_PACKET = "SIMPLE_PACKET"
    UNKNOWN = "UNKNOWN"


class TestStatus(Enum):
    """Test status enumeration."""

    ETH_ACTIVE = "ETH_ACTIVE"
    ETH_UNCONNECTED = "ETH_UNCONNECTED"
    TRAINING_FAIL = "TRAINING_FAIL"
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class PortType(Enum):
    """Ethernet port type enumeration."""

    CHIP_TO_CHIP = "CHIP_TO_CHIP"
    CHIP_TO_QSFPDD = "CHIP_TO_QSFPDD"
    UNKNOWN = "UNKNOWN"


class TrainMode(Enum):
    """Training mode enumeration."""

    AW_MANUAL_EQ = "AW_MANUAL_EQ"
    AW_ANLT_MODE = "AW_ANLT_MODE"
    UNKNOWN = "UNKNOWN"


@dataclass
class TestResult:
    """Represents a single test result from CSV data.

    Attributes:
        test_id: Unique identifier for the test run
        bus_id: PCIe bus ID identifying the chip
        eth_port: Ethernet port identifier (e.g., ETH00, ETH01)
        test_status: Status of the test (e.g., ETH_ACTIVE, TRAINING_FAIL)
        test_type: Type of test (SERDES_PRBS or SIMPLE_PACKET)
        data: Additional test data as dictionary
    """

    bus_id: str
    eth_port: str
    test_status: TestStatus
    test_type: TestType
    test_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Convert string status/type to enums if needed."""
        if isinstance(self.test_status, str):
            try:
                self.test_status = TestStatus[self.test_status]
            except KeyError:
                self.test_status = TestStatus.UNKNOWN

        if isinstance(self.test_type, str):
            try:
                self.test_type = TestType[self.test_type]
            except KeyError:
                self.test_type = TestType.UNKNOWN


@dataclass
class FailureSignature:
    """Represents a failure pattern signature.

    Attributes:
        pattern_name: Name of the failure pattern (e.g., "CDR_UNLOCK_PATTERN")
        indicators: Dictionary of diagnostic indicators
        port_type: Type of port where failure occurred
        train_mode: Training mode when failure occurred
        description: Optional description of the failure pattern
    """

    pattern_name: str
    indicators: Dict[str, Any]
    port_type: PortType
    train_mode: TrainMode
    description: Optional[str] = None

    def __post_init__(self):
        """Convert string port_type/train_mode to enums if needed."""
        if isinstance(self.port_type, str):
            try:
                self.port_type = PortType[self.port_type]
            except KeyError:
                self.port_type = PortType.UNKNOWN

        if isinstance(self.train_mode, str):
            try:
                self.train_mode = TrainMode[self.train_mode]
            except KeyError:
                self.train_mode = TrainMode.UNKNOWN


@dataclass
class FailureRecord:
    """Represents a failure with its diagnostic information.

    Attributes:
        test_result: The test result that failed
        failure_signature: The identified failure signature
        diagnostic_data: Additional diagnostic information
        connected_port: Information about the connected port (if applicable)
    """

    test_result: TestResult
    failure_signature: Optional[FailureSignature] = None
    diagnostic_data: Dict[str, Any] = field(default_factory=dict)
    connected_port: Optional["PortMetadata"] = None


@dataclass
class SystemConfig:
    """Represents system configuration metadata.

    Attributes:
        hostname: System hostname (e.g., bh-glx-b02u02)
        firmware_version: Firmware version string (e.g., erisc_v1_7_103)
        test_type: Type of test being run
        serial_number: Optional system serial number
        metadata: Additional configuration metadata
    """

    hostname: str
    firmware_version: str
    test_type: TestType
    serial_number: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PortMetadata:
    """Represents Ethernet port metadata.

    Attributes:
        bus_id: PCIe bus ID of the chip
        eth_port: Ethernet port identifier
        port_type: Type of connection (CHIP_TO_CHIP or CHIP_TO_QSFPDD)
        connected_bus_id: Bus ID of connected chip (for CHIP_TO_CHIP)
        connected_eth_port: Ethernet port of connected chip
        cable_connector: Whether this port connects to a cable connector
        serdes_pair: Related port in the serdes pair (lead/follower)
    """

    bus_id: str
    eth_port: str
    port_type: PortType
    connected_bus_id: Optional[str] = None
    connected_eth_port: Optional[str] = None
    cable_connector: bool = False
    serdes_pair: Optional[str] = None

    def __post_init__(self):
        """Convert string port_type to enum if needed."""
        if isinstance(self.port_type, str):
            try:
                self.port_type = PortType[self.port_type]
            except KeyError:
                self.port_type = PortType.UNKNOWN


@dataclass
class QC3TestResult:
    """Represents a QC3 (Quanta) test result from Excel.

    Attributes:
        serial_number: System serial number
        asic: ASIC identifier
        port: Port identifier
        failure_count: Number of failures detected
        test_type: Type of test
        metadata: Additional test metadata
    """

    serial_number: str
    asic: str
    port: str
    failure_count: int
    test_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JiraConfig:
    """Jira configuration.

    Attributes:
        server_url: Jira server URL
        email: User email for authentication
        api_key: API key for authentication
    """

    server_url: str
    email: str
    api_key: str


@dataclass
class DataConfig:
    """Data processing configuration.

    Attributes:
        input_dir: Directory containing input CSV files
        output_dir: Directory for output files
        temp_dir: Optional temporary directory
    """

    input_dir: Path = Path("csv_data")
    output_dir: Path = Path("summaries")
    temp_dir: Optional[Path] = None

    def __post_init__(self):
        """Ensure paths are Path objects."""
        self.input_dir = Path(self.input_dir)
        self.output_dir = Path(self.output_dir)
        if self.temp_dir:
            self.temp_dir = Path(self.temp_dir)


@dataclass
class Config:
    """Main configuration object.

    Attributes:
        jira: Jira configuration
        data: Data processing configuration
    """

    jira: JiraConfig
    data: DataConfig


@dataclass
class ExtractionResult:
    """Result of archive extraction operation.

    Attributes:
        extracted_files: List of extracted file paths
        failed_serials: List of serial numbers that failed
        total_files: Total number of files extracted
        success: Whether the extraction was successful
        error_message: Optional error message if extraction failed
    """

    extracted_files: List[Path]
    failed_serials: List[str]
    total_files: int
    success: bool
    error_message: Optional[str] = None


@dataclass
class DownloadResult:
    """Result of Jira download operation.

    Attributes:
        downloaded_files: List of downloaded file paths
        failed_tickets: List of ticket keys that failed
        total_downloads: Total number of successful downloads
        success: Whether the download operation was successful
        error_message: Optional error message if download failed
    """

    downloaded_files: List[Path]
    failed_tickets: List[str]
    total_downloads: int
    success: bool
    error_message: Optional[str] = None


@dataclass
class FilterResult:
    """Result of failure filtering operation.

    Attributes:
        input_file: Path to input CSV file
        output_file: Path to output CSV file with failures
        total_rows: Total number of rows in input
        failure_count: Number of failures found
        failure_breakdown: Dictionary of failure counts by status
        success: Whether the filtering was successful
        error_message: Optional error message if filtering failed
    """

    input_file: Path
    output_file: Path
    total_rows: int
    failure_count: int
    failure_breakdown: Dict[str, int]
    success: bool
    error_message: Optional[str] = None


@dataclass
class AnalysisResult:
    """Result of failure analysis operation.

    Attributes:
        input_file: Path to input CSV file
        output_dir: Directory where reports were generated
        failure_records: List of failure records found
        signature_summary: Summary of failure signatures
        total_failures: Total number of failures analyzed
        success: Whether the analysis was successful
        error_message: Optional error message if analysis failed
    """

    input_file: Path
    output_dir: Path
    failure_records: List[FailureRecord]
    signature_summary: Dict[str, int]
    total_failures: int
    success: bool
    error_message: Optional[str] = None
