"""Unit tests for bh_glx_data.core.exceptions module."""

import pytest

from bh_glx_data.core.exceptions import (
    BHGlxDataError,
    ConfigurationError,
    CSVParseError,
    DataProcessingError,
    ExcelGenerationError,
    JiraAuthenticationError,
    JiraConnectionError,
    TemplateError,
    ValidationError,
)


@pytest.mark.unit
class TestBHGlxDataError:
    """Test cases for BHGlxDataError base exception."""

    def test_base_exception_creation(self):
        """Test that base exception can be created with a message."""
        error = BHGlxDataError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"

    def test_base_exception_inheritance(self):
        """Test that BHGlxDataError inherits from Exception."""
        error = BHGlxDataError("Test")
        assert isinstance(error, Exception)


@pytest.mark.unit
class TestConfigurationErrors:
    """Test cases for configuration-related exceptions."""

    def test_configuration_error(self):
        """Test ConfigurationError exception."""
        error = ConfigurationError("Invalid configuration")
        assert isinstance(error, BHGlxDataError)
        assert str(error) == "Invalid configuration"

    def test_validation_error(self):
        """Test ValidationError exception."""
        error = ValidationError("Validation failed")
        assert isinstance(error, BHGlxDataError)
        assert str(error) == "Validation failed"


@pytest.mark.unit
class TestDataProcessingErrors:
    """Test cases for data processing exceptions."""

    def test_data_processing_error(self):
        """Test DataProcessingError exception."""
        error = DataProcessingError("Data processing failed")
        assert isinstance(error, BHGlxDataError)
        assert str(error) == "Data processing failed"

    def test_csv_parse_error_basic(self):
        """Test CSVParseError with just message."""
        error = CSVParseError("Parse error")
        assert isinstance(error, DataProcessingError)
        assert str(error) == "Parse error"

    def test_csv_parse_error_with_file(self):
        """Test CSVParseError with file path."""
        error = CSVParseError("Parse error", file_path="/path/to/file.csv")
        assert "Parse error" in str(error)
        assert "/path/to/file.csv" in str(error)
        assert error.file_path == "/path/to/file.csv"
        assert error.line_number is None

    def test_csv_parse_error_with_line_number(self):
        """Test CSVParseError with line number."""
        error = CSVParseError("Parse error", line_number=42)
        assert "Parse error" in str(error)
        assert "42" in str(error)
        assert error.file_path is None
        assert error.line_number == 42

    def test_csv_parse_error_full(self):
        """Test CSVParseError with all parameters."""
        error = CSVParseError("Parse error", file_path="/path/to/file.csv", line_number=42)
        error_str = str(error)
        assert "Parse error" in error_str
        assert "/path/to/file.csv" in error_str
        assert "42" in error_str
        assert error.file_path == "/path/to/file.csv"
        assert error.line_number == 42


@pytest.mark.unit
class TestJiraErrors:
    """Test cases for Jira integration exceptions."""

    def test_jira_connection_error_basic(self):
        """Test JiraConnectionError with just message."""
        error = JiraConnectionError("Connection failed")
        assert isinstance(error, BHGlxDataError)
        assert str(error) == "Connection failed"
        assert error.server_url is None

    def test_jira_connection_error_with_url(self):
        """Test JiraConnectionError with server URL."""
        error = JiraConnectionError("Connection failed", server_url="https://example.atlassian.net")
        error_str = str(error)
        assert "Connection failed" in error_str
        assert "https://example.atlassian.net" in error_str
        assert error.server_url == "https://example.atlassian.net"

    def test_jira_authentication_error_basic(self):
        """Test JiraAuthenticationError with just message."""
        error = JiraAuthenticationError("Authentication failed")
        assert isinstance(error, BHGlxDataError)
        assert str(error) == "Authentication failed"
        assert error.email is None

    def test_jira_authentication_error_with_email(self):
        """Test JiraAuthenticationError with email."""
        error = JiraAuthenticationError("Authentication failed", email="test@example.com")
        error_str = str(error)
        assert "Authentication failed" in error_str
        assert "test@example.com" in error_str
        assert error.email == "test@example.com"


@pytest.mark.unit
class TestExcelErrors:
    """Test cases for Excel reporting exceptions."""

    def test_excel_generation_error_basic(self):
        """Test ExcelGenerationError with just message."""
        error = ExcelGenerationError("Generation failed")
        assert isinstance(error, BHGlxDataError)
        assert str(error) == "Generation failed"
        assert error.output_path is None

    def test_excel_generation_error_with_path(self):
        """Test ExcelGenerationError with output path."""
        error = ExcelGenerationError("Generation failed", output_path="/path/to/output.xlsx")
        error_str = str(error)
        assert "Generation failed" in error_str
        assert "/path/to/output.xlsx" in error_str
        assert error.output_path == "/path/to/output.xlsx"

    def test_template_error_basic(self):
        """Test TemplateError with just message."""
        error = TemplateError("Template error")
        assert isinstance(error, ExcelGenerationError)
        assert isinstance(error, BHGlxDataError)
        assert str(error) == "Template error"
        assert error.template_path is None

    def test_template_error_with_path(self):
        """Test TemplateError with template path."""
        error = TemplateError("Template error", template_path="/path/to/template.xlsx")
        error_str = str(error)
        assert "Template error" in error_str
        assert "/path/to/template.xlsx" in error_str
        assert error.template_path == "/path/to/template.xlsx"


@pytest.mark.unit
class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from BHGlxDataError."""
        exceptions = [
            ConfigurationError("test"),
            ValidationError("test"),
            DataProcessingError("test"),
            CSVParseError("test"),
            JiraConnectionError("test"),
            JiraAuthenticationError("test"),
            ExcelGenerationError("test"),
            TemplateError("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, BHGlxDataError)
            assert isinstance(exc, Exception)

    def test_specific_inheritances(self):
        """Test specific inheritance relationships."""
        # CSVParseError inherits from DataProcessingError
        assert isinstance(CSVParseError("test"), DataProcessingError)

        # TemplateError inherits from ExcelGenerationError
        assert isinstance(TemplateError("test"), ExcelGenerationError)

    def test_exception_catching(self):
        """Test that exceptions can be caught by base class."""
        try:
            raise CSVParseError("Test error")
        except BHGlxDataError as e:
            assert str(e) == "Test error"
        else:
            pytest.fail("Exception was not caught")

    def test_multiple_inheritance_levels(self):
        """Test catching with intermediate base classes."""
        try:
            raise CSVParseError("Test error")
        except DataProcessingError as e:
            assert isinstance(e, BHGlxDataError)
        else:
            pytest.fail("Exception was not caught")


@pytest.mark.unit
class TestExceptionMessages:
    """Test exception message formatting."""

    def test_exception_string_representations(self):
        """Test that all exceptions have proper string representations."""
        test_cases = [
            (BHGlxDataError("test"), "test"),
            (ConfigurationError("config error"), "config error"),
            (ValidationError("validation error"), "validation error"),
            (DataProcessingError("processing error"), "processing error"),
            (CSVParseError("parse error"), "parse error"),
            (JiraConnectionError("connection error"), "connection error"),
            (JiraAuthenticationError("auth error"), "auth error"),
            (ExcelGenerationError("excel error"), "excel error"),
            (TemplateError("template error"), "template error"),
        ]

        for exception, expected_message in test_cases:
            assert expected_message in str(exception)

    def test_exception_attributes_preserved(self):
        """Test that exception attributes are properly preserved."""
        # Test CSVParseError
        csv_error = CSVParseError("error", file_path="test.csv", line_number=10)
        assert csv_error.message == "error"
        assert csv_error.file_path == "test.csv"
        assert csv_error.line_number == 10

        # Test JiraConnectionError
        jira_error = JiraConnectionError("error", server_url="https://example.com")
        assert jira_error.message == "error"
        assert jira_error.server_url == "https://example.com"

        # Test JiraAuthenticationError
        auth_error = JiraAuthenticationError("error", email="test@example.com")
        assert auth_error.message == "error"
        assert auth_error.email == "test@example.com"
