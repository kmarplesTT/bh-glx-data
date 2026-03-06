"""Core abstractions for BH Galaxy Data Analysis Tool.

This module provides core abstractions including:
- Configuration management
- Data models
- Custom exceptions
"""

from bh_glx_data.core.config import ConfigManager, get_config, load_config
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

__all__ = [
    # Configuration
    "ConfigManager",
    "load_config",
    "get_config",
    # Exceptions
    "BHGlxDataError",
    "ConfigurationError",
    "ValidationError",
    "DataProcessingError",
    "CSVParseError",
    "JiraConnectionError",
    "JiraAuthenticationError",
    "ExcelGenerationError",
    "TemplateError",
    # Models
    "Config",
    "JiraConfig",
    "DataConfig",
    "TestResult",
    "TestStatus",
    "TestType",
    "FailureSignature",
    "FailureRecord",
    "SystemConfig",
    "PortMetadata",
    "PortType",
    "TrainMode",
    "QC3TestResult",
    "ExtractionResult",
    "DownloadResult",
    "FilterResult",
    "AnalysisResult",
]
