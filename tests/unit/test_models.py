"""Unit tests for bh_glx_data.core.models module."""

from pathlib import Path

import pytest

from bh_glx_data.core.models import (
    AnalysisResult,
    Config,
    DataConfig,
    DownloadResult,
    ExtractionResult,
    FailureRecord,
    FailureSignature,
    FilterResult,
    JiraConfig,
    PortMetadata,
    PortType,
    QC3TestResult,
    SystemConfig,
    TestResult,
    TestStatus,
    TestType,
    TrainMode,
)


@pytest.mark.unit
class TestEnums:
    """Test cases for enum types."""

    def test_test_type_enum(self):
        """Test TestType enum values."""
        assert TestType.SERDES_PRBS.value == "SERDES_PRBS"
        assert TestType.SIMPLE_PACKET.value == "SIMPLE_PACKET"
        assert TestType.UNKNOWN.value == "UNKNOWN"

    def test_test_status_enum(self):
        """Test TestStatus enum values."""
        assert TestStatus.ETH_ACTIVE.value == "ETH_ACTIVE"
        assert TestStatus.ETH_UNCONNECTED.value == "ETH_UNCONNECTED"
        assert TestStatus.TRAINING_FAIL.value == "TRAINING_FAIL"
        assert TestStatus.PASS.value == "PASS"
        assert TestStatus.FAIL.value == "FAIL"
        assert TestStatus.UNKNOWN.value == "UNKNOWN"

    def test_port_type_enum(self):
        """Test PortType enum values."""
        assert PortType.CHIP_TO_CHIP.value == "CHIP_TO_CHIP"
        assert PortType.CHIP_TO_QSFPDD.value == "CHIP_TO_QSFPDD"
        assert PortType.UNKNOWN.value == "UNKNOWN"

    def test_train_mode_enum(self):
        """Test TrainMode enum values."""
        assert TrainMode.AW_MANUAL_EQ.value == "AW_MANUAL_EQ"
        assert TrainMode.AW_ANLT_MODE.value == "AW_ANLT_MODE"
        assert TrainMode.UNKNOWN.value == "UNKNOWN"


@pytest.mark.unit
class TestTestResult:
    """Test cases for TestResult dataclass."""

    def test_basic_creation(self):
        """Test creating TestResult with basic parameters."""
        result = TestResult(
            bus_id="01:00.0",
            eth_port="ETH00",
            test_status=TestStatus.ETH_ACTIVE,
            test_type=TestType.SERDES_PRBS,
        )
        assert result.bus_id == "01:00.0"
        assert result.eth_port == "ETH00"
        assert result.test_status == TestStatus.ETH_ACTIVE
        assert result.test_type == TestType.SERDES_PRBS
        assert result.test_id is None
        assert result.data == {}

    def test_with_test_id_and_data(self):
        """Test creating TestResult with optional parameters."""
        data = {"host": "bh-glx-b02u02", "lcpll_lock_fail_cnt": 0}
        result = TestResult(
            test_id="test_001",
            bus_id="01:00.0",
            eth_port="ETH00",
            test_status=TestStatus.ETH_ACTIVE,
            test_type=TestType.SERDES_PRBS,
            data=data,
        )
        assert result.test_id == "test_001"
        assert result.data == data

    def test_string_to_enum_conversion_status(self):
        """Test that string test_status is converted to enum."""
        result = TestResult(
            bus_id="01:00.0",
            eth_port="ETH00",
            test_status="ETH_ACTIVE",
            test_type=TestType.SERDES_PRBS,
        )
        assert result.test_status == TestStatus.ETH_ACTIVE
        assert isinstance(result.test_status, TestStatus)

    def test_string_to_enum_conversion_type(self):
        """Test that string test_type is converted to enum."""
        result = TestResult(
            bus_id="01:00.0",
            eth_port="ETH00",
            test_status=TestStatus.ETH_ACTIVE,
            test_type="SERDES_PRBS",
        )
        assert result.test_type == TestType.SERDES_PRBS
        assert isinstance(result.test_type, TestType)

    def test_unknown_status_conversion(self):
        """Test that unknown status string converts to UNKNOWN enum."""
        result = TestResult(
            bus_id="01:00.0",
            eth_port="ETH00",
            test_status="INVALID_STATUS",
            test_type=TestType.SERDES_PRBS,
        )
        assert result.test_status == TestStatus.UNKNOWN

    def test_unknown_type_conversion(self):
        """Test that unknown type string converts to UNKNOWN enum."""
        result = TestResult(
            bus_id="01:00.0",
            eth_port="ETH00",
            test_status=TestStatus.ETH_ACTIVE,
            test_type="INVALID_TYPE",
        )
        assert result.test_type == TestType.UNKNOWN


@pytest.mark.unit
class TestFailureSignature:
    """Test cases for FailureSignature dataclass."""

    def test_basic_creation(self):
        """Test creating FailureSignature with basic parameters."""
        signature = FailureSignature(
            pattern_name="CDR_UNLOCK_PATTERN",
            indicators={"cdr_unlock_cnt": ">0"},
            port_type=PortType.CHIP_TO_QSFPDD,
            train_mode=TrainMode.AW_MANUAL_EQ,
        )
        assert signature.pattern_name == "CDR_UNLOCK_PATTERN"
        assert signature.indicators == {"cdr_unlock_cnt": ">0"}
        assert signature.port_type == PortType.CHIP_TO_QSFPDD
        assert signature.train_mode == TrainMode.AW_MANUAL_EQ
        assert signature.description is None

    def test_with_description(self):
        """Test creating FailureSignature with description."""
        signature = FailureSignature(
            pattern_name="TEST_PATTERN",
            indicators={},
            port_type=PortType.CHIP_TO_CHIP,
            train_mode=TrainMode.AW_ANLT_MODE,
            description="Test pattern description",
        )
        assert signature.description == "Test pattern description"

    def test_string_to_enum_conversion(self):
        """Test that string port_type and train_mode are converted to enums."""
        signature = FailureSignature(
            pattern_name="TEST",
            indicators={},
            port_type="CHIP_TO_CHIP",
            train_mode="AW_MANUAL_EQ",
        )
        assert signature.port_type == PortType.CHIP_TO_CHIP
        assert signature.train_mode == TrainMode.AW_MANUAL_EQ
        assert isinstance(signature.port_type, PortType)
        assert isinstance(signature.train_mode, TrainMode)

    def test_unknown_enum_conversion(self):
        """Test that unknown strings convert to UNKNOWN enums."""
        signature = FailureSignature(
            pattern_name="TEST",
            indicators={},
            port_type="INVALID_PORT_TYPE",
            train_mode="INVALID_TRAIN_MODE",
        )
        assert signature.port_type == PortType.UNKNOWN
        assert signature.train_mode == TrainMode.UNKNOWN


@pytest.mark.unit
class TestFailureRecord:
    """Test cases for FailureRecord dataclass."""

    def test_basic_creation(self, sample_failure_result):
        """Test creating FailureRecord with test result."""
        record = FailureRecord(test_result=sample_failure_result)
        assert record.test_result == sample_failure_result
        assert record.failure_signature is None
        assert record.diagnostic_data == {}
        assert record.connected_port is None

    def test_with_all_fields(self, sample_failure_result, sample_failure_signature, sample_port_metadata):
        """Test creating FailureRecord with all fields."""
        diagnostic = {"cdr_unlock_cnt": 5, "retry_cnt": 10}
        record = FailureRecord(
            test_result=sample_failure_result,
            failure_signature=sample_failure_signature,
            diagnostic_data=diagnostic,
            connected_port=sample_port_metadata,
        )
        assert record.test_result == sample_failure_result
        assert record.failure_signature == sample_failure_signature
        assert record.diagnostic_data == diagnostic
        assert record.connected_port == sample_port_metadata


@pytest.mark.unit
class TestSystemConfig:
    """Test cases for SystemConfig dataclass."""

    def test_basic_creation(self):
        """Test creating SystemConfig with required parameters."""
        config = SystemConfig(
            hostname="bh-glx-b02u02",
            firmware_version="erisc_v1_7_103",
            test_type=TestType.SERDES_PRBS,
        )
        assert config.hostname == "bh-glx-b02u02"
        assert config.firmware_version == "erisc_v1_7_103"
        assert config.test_type == TestType.SERDES_PRBS
        assert config.serial_number is None
        assert config.metadata == {}

    def test_with_all_fields(self):
        """Test creating SystemConfig with all fields."""
        metadata = {"board_id": "UBB1", "slot": "U1"}
        config = SystemConfig(
            hostname="bh-glx-b02u02",
            firmware_version="erisc_v1_7_103",
            test_type=TestType.SIMPLE_PACKET,
            serial_number="SN12345",
            metadata=metadata,
        )
        assert config.serial_number == "SN12345"
        assert config.metadata == metadata


@pytest.mark.unit
class TestPortMetadata:
    """Test cases for PortMetadata dataclass."""

    def test_basic_creation(self):
        """Test creating PortMetadata with required parameters."""
        port = PortMetadata(
            bus_id="01:00.0",
            eth_port="ETH00",
            port_type=PortType.CHIP_TO_CHIP,
        )
        assert port.bus_id == "01:00.0"
        assert port.eth_port == "ETH00"
        assert port.port_type == PortType.CHIP_TO_CHIP
        assert port.connected_bus_id is None
        assert port.connected_eth_port is None
        assert port.cable_connector is False
        assert port.serdes_pair is None

    def test_with_all_fields(self):
        """Test creating PortMetadata with all fields."""
        port = PortMetadata(
            bus_id="01:00.0",
            eth_port="ETH00",
            port_type=PortType.CHIP_TO_CHIP,
            connected_bus_id="02:00.0",
            connected_eth_port="ETH01",
            cable_connector=True,
            serdes_pair="ETH01",
        )
        assert port.connected_bus_id == "02:00.0"
        assert port.connected_eth_port == "ETH01"
        assert port.cable_connector is True
        assert port.serdes_pair == "ETH01"

    def test_string_to_enum_conversion(self):
        """Test that string port_type is converted to enum."""
        port = PortMetadata(
            bus_id="01:00.0",
            eth_port="ETH00",
            port_type="CHIP_TO_QSFPDD",
        )
        assert port.port_type == PortType.CHIP_TO_QSFPDD
        assert isinstance(port.port_type, PortType)

    def test_unknown_port_type_conversion(self):
        """Test that unknown port_type string converts to UNKNOWN enum."""
        port = PortMetadata(
            bus_id="01:00.0",
            eth_port="ETH00",
            port_type="INVALID_TYPE",
        )
        assert port.port_type == PortType.UNKNOWN


@pytest.mark.unit
class TestQC3TestResult:
    """Test cases for QC3TestResult dataclass."""

    def test_basic_creation(self):
        """Test creating QC3TestResult."""
        result = QC3TestResult(
            serial_number="SN12345",
            asic="U1",
            port="ETH00",
            failure_count=5,
            test_type="PRBS",
        )
        assert result.serial_number == "SN12345"
        assert result.asic == "U1"
        assert result.port == "ETH00"
        assert result.failure_count == 5
        assert result.test_type == "PRBS"
        assert result.metadata == {}

    def test_with_metadata(self):
        """Test creating QC3TestResult with metadata."""
        metadata = {"timestamp": "2024-01-01", "operator": "test_user"}
        result = QC3TestResult(
            serial_number="SN12345",
            asic="U1",
            port="ETH00",
            failure_count=0,
            test_type="DATA",
            metadata=metadata,
        )
        assert result.metadata == metadata


@pytest.mark.unit
class TestJiraConfig:
    """Test cases for JiraConfig dataclass."""

    def test_creation(self):
        """Test creating JiraConfig."""
        config = JiraConfig(
            server_url="https://example.atlassian.net",
            email="test@example.com",
            api_key="test-api-key",
        )
        assert config.server_url == "https://example.atlassian.net"
        assert config.email == "test@example.com"
        assert config.api_key == "test-api-key"


@pytest.mark.unit
class TestDataConfig:
    """Test cases for DataConfig dataclass."""

    def test_default_values(self):
        """Test DataConfig with default values."""
        config = DataConfig()
        assert config.input_dir == Path("csv_data")
        assert config.output_dir == Path("summaries")
        assert config.temp_dir is None

    def test_custom_values(self):
        """Test DataConfig with custom values."""
        config = DataConfig(
            input_dir=Path("/custom/input"),
            output_dir=Path("/custom/output"),
            temp_dir=Path("/custom/temp"),
        )
        assert config.input_dir == Path("/custom/input")
        assert config.output_dir == Path("/custom/output")
        assert config.temp_dir == Path("/custom/temp")

    def test_string_to_path_conversion(self):
        """Test that string paths are converted to Path objects."""
        config = DataConfig(
            input_dir="input_str",
            output_dir="output_str",
            temp_dir="temp_str",
        )
        assert isinstance(config.input_dir, Path)
        assert isinstance(config.output_dir, Path)
        assert isinstance(config.temp_dir, Path)
        assert config.input_dir == Path("input_str")
        assert config.output_dir == Path("output_str")
        assert config.temp_dir == Path("temp_str")


@pytest.mark.unit
class TestConfig:
    """Test cases for Config dataclass."""

    def test_creation(self, sample_jira_config, sample_data_config):
        """Test creating Config."""
        config = Config(jira=sample_jira_config, data=sample_data_config)
        assert config.jira == sample_jira_config
        assert config.data == sample_data_config


@pytest.mark.unit
class TestExtractionResult:
    """Test cases for ExtractionResult dataclass."""

    def test_success_result(self):
        """Test creating successful ExtractionResult."""
        result = ExtractionResult(
            extracted_files=[Path("file1.csv"), Path("file2.csv")],
            failed_serials=["SN001", "SN002"],
            total_files=2,
            success=True,
        )
        assert len(result.extracted_files) == 2
        assert len(result.failed_serials) == 2
        assert result.total_files == 2
        assert result.success is True
        assert result.error_message is None

    def test_failure_result(self):
        """Test creating failed ExtractionResult."""
        result = ExtractionResult(
            extracted_files=[],
            failed_serials=[],
            total_files=0,
            success=False,
            error_message="Archive extraction failed",
        )
        assert result.success is False
        assert result.error_message == "Archive extraction failed"


@pytest.mark.unit
class TestDownloadResult:
    """Test cases for DownloadResult dataclass."""

    def test_success_result(self):
        """Test creating successful DownloadResult."""
        result = DownloadResult(
            downloaded_files=[Path("file1.csv"), Path("file2.csv")],
            failed_tickets=["SYS-123"],
            total_downloads=2,
            success=True,
        )
        assert len(result.downloaded_files) == 2
        assert result.failed_tickets == ["SYS-123"]
        assert result.total_downloads == 2
        assert result.success is True
        assert result.error_message is None

    def test_failure_result(self):
        """Test creating failed DownloadResult."""
        result = DownloadResult(
            downloaded_files=[],
            failed_tickets=["SYS-123", "SYS-456"],
            total_downloads=0,
            success=False,
            error_message="Jira connection failed",
        )
        assert result.success is False
        assert result.error_message == "Jira connection failed"
        assert len(result.failed_tickets) == 2


@pytest.mark.unit
class TestFilterResult:
    """Test cases for FilterResult dataclass."""

    def test_success_result(self):
        """Test creating successful FilterResult."""
        result = FilterResult(
            input_file=Path("input.csv"),
            output_file=Path("output.csv"),
            total_rows=100,
            failure_count=10,
            failure_breakdown={"TRAINING_FAIL": 8, "FAIL": 2},
            success=True,
        )
        assert result.input_file == Path("input.csv")
        assert result.output_file == Path("output.csv")
        assert result.total_rows == 100
        assert result.failure_count == 10
        assert result.failure_breakdown == {"TRAINING_FAIL": 8, "FAIL": 2}
        assert result.success is True
        assert result.error_message is None

    def test_failure_result(self):
        """Test creating failed FilterResult."""
        result = FilterResult(
            input_file=Path("input.csv"),
            output_file=Path("output.csv"),
            total_rows=0,
            failure_count=0,
            failure_breakdown={},
            success=False,
            error_message="File not found",
        )
        assert result.success is False
        assert result.error_message == "File not found"


@pytest.mark.unit
class TestAnalysisResult:
    """Test cases for AnalysisResult dataclass."""

    def test_success_result(self, sample_failure_result, sample_failure_signature):
        """Test creating successful AnalysisResult."""
        failure_record = FailureRecord(
            test_result=sample_failure_result,
            failure_signature=sample_failure_signature,
        )
        result = AnalysisResult(
            input_file=Path("input.csv"),
            output_dir=Path("reports"),
            failure_records=[failure_record],
            signature_summary={"CDR_UNLOCK_PATTERN": 5},
            total_failures=5,
            success=True,
        )
        assert result.input_file == Path("input.csv")
        assert result.output_dir == Path("reports")
        assert len(result.failure_records) == 1
        assert result.signature_summary == {"CDR_UNLOCK_PATTERN": 5}
        assert result.total_failures == 5
        assert result.success is True
        assert result.error_message is None

    def test_failure_result(self):
        """Test creating failed AnalysisResult."""
        result = AnalysisResult(
            input_file=Path("input.csv"),
            output_dir=Path("reports"),
            failure_records=[],
            signature_summary={},
            total_failures=0,
            success=False,
            error_message="Analysis failed",
        )
        assert result.success is False
        assert result.error_message == "Analysis failed"


@pytest.mark.unit
class TestModelIntegration:
    """Test integration between different models."""

    def test_complete_failure_workflow(
        self,
        sample_failure_result,
        sample_failure_signature,
        sample_port_metadata,
    ):
        """Test complete workflow from test result to failure record."""
        # Create a failure record with all components
        record = FailureRecord(
            test_result=sample_failure_result,
            failure_signature=sample_failure_signature,
            diagnostic_data={"cdr_unlock_cnt": 5, "retry_cnt": 10},
            connected_port=sample_port_metadata,
        )

        # Verify all components are linked correctly
        assert record.test_result.test_status == TestStatus.TRAINING_FAIL
        assert record.failure_signature.pattern_name == "CDR_UNLOCK_PATTERN"
        assert record.connected_port.bus_id == "01:00.0"
        assert "cdr_unlock_cnt" in record.diagnostic_data

    def test_system_config_with_test_result(self, sample_test_result):
        """Test SystemConfig with test result."""
        system_config = SystemConfig(
            hostname="bh-glx-b02u02",
            firmware_version="erisc_v1_7_103",
            test_type=sample_test_result.test_type,
            serial_number="SN12345",
        )

        assert system_config.test_type == sample_test_result.test_type
        assert system_config.hostname == "bh-glx-b02u02"


@pytest.mark.unit
class TestModelEquality:
    """Test equality operations on models."""

    def test_test_result_equality(self):
        """Test that identical TestResults are equal."""
        result1 = TestResult(
            bus_id="01:00.0",
            eth_port="ETH00",
            test_status=TestStatus.ETH_ACTIVE,
            test_type=TestType.SERDES_PRBS,
        )
        result2 = TestResult(
            bus_id="01:00.0",
            eth_port="ETH00",
            test_status=TestStatus.ETH_ACTIVE,
            test_type=TestType.SERDES_PRBS,
        )
        assert result1 == result2

    def test_config_equality(self):
        """Test that identical Configs are equal."""
        jira1 = JiraConfig(
            server_url="https://example.com",
            email="test@example.com",
            api_key="key123",
        )
        jira2 = JiraConfig(
            server_url="https://example.com",
            email="test@example.com",
            api_key="key123",
        )
        data1 = DataConfig()
        data2 = DataConfig()

        config1 = Config(jira=jira1, data=data1)
        config2 = Config(jira=jira2, data=data2)

        assert config1 == config2
