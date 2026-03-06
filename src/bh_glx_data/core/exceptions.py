"""Custom exceptions for BH Galaxy Data Analysis Tool.

This module defines a hierarchy of exceptions for different error conditions
that can occur during data collection, processing, and analysis.
"""


class BHGlxDataError(Exception):
    """Base exception for all BH Galaxy Data Analysis Tool errors."""

    def __init__(self, message: str, *args, **kwargs):
        """Initialize the exception with a message.

        Args:
            message: Error message describing the problem
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        super().__init__(message, *args, **kwargs)
        self.message = message


# Configuration Errors


class ConfigurationError(BHGlxDataError):
    """Raised when there is an error in configuration loading or parsing."""

    pass


class ValidationError(BHGlxDataError):
    """Raised when configuration or data validation fails."""

    pass


# Data Processing Errors


class DataProcessingError(BHGlxDataError):
    """Base exception for data processing errors."""

    pass


class CSVParseError(DataProcessingError):
    """Raised when CSV parsing fails."""

    def __init__(self, message: str, file_path: str = None, line_number: int = None):
        """Initialize CSV parse error.

        Args:
            message: Error message
            file_path: Path to the CSV file that failed to parse
            line_number: Line number where parsing failed
        """
        super().__init__(message)
        self.file_path = file_path
        self.line_number = line_number

    def __str__(self):
        """Return string representation with file and line info."""
        parts = [self.message]
        if self.file_path:
            parts.append(f"File: {self.file_path}")
        if self.line_number:
            parts.append(f"Line: {self.line_number}")
        return " | ".join(parts)


# Jira Integration Errors


class JiraConnectionError(BHGlxDataError):
    """Raised when connection to Jira fails."""

    def __init__(self, message: str, server_url: str = None):
        """Initialize Jira connection error.

        Args:
            message: Error message
            server_url: Jira server URL that failed to connect
        """
        super().__init__(message)
        self.server_url = server_url

    def __str__(self):
        """Return string representation with server URL."""
        if self.server_url:
            return f"{self.message} (Server: {self.server_url})"
        return self.message


class JiraAuthenticationError(BHGlxDataError):
    """Raised when Jira authentication fails."""

    def __init__(self, message: str, email: str = None):
        """Initialize Jira authentication error.

        Args:
            message: Error message
            email: Email used for authentication
        """
        super().__init__(message)
        self.email = email

    def __str__(self):
        """Return string representation with email."""
        if self.email:
            return f"{self.message} (Email: {self.email})"
        return self.message


# Excel Reporting Errors


class ExcelGenerationError(BHGlxDataError):
    """Raised when Excel file generation fails."""

    def __init__(self, message: str, output_path: str = None):
        """Initialize Excel generation error.

        Args:
            message: Error message
            output_path: Path where Excel file was being generated
        """
        super().__init__(message)
        self.output_path = output_path

    def __str__(self):
        """Return string representation with output path."""
        if self.output_path:
            return f"{self.message} (Output: {self.output_path})"
        return self.message


class TemplateError(ExcelGenerationError):
    """Raised when there is an error with Excel template."""

    def __init__(self, message: str, template_path: str = None):
        """Initialize template error.

        Args:
            message: Error message
            template_path: Path to the template file
        """
        super().__init__(message)
        self.template_path = template_path

    def __str__(self):
        """Return string representation with template path."""
        if self.template_path:
            return f"{self.message} (Template: {self.template_path})"
        return self.message
