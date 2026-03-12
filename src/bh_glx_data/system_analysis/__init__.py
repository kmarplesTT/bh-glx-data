"""System Analysis Module for BH Galaxy Data Analysis Tool.

This module provides database-backed analysis capabilities for PRBS test data
across multiple systems, including:

- SQLite database storage with indexed queries
- Streaming CSV ingestion with filtering
- Flexible lane selection and query interface
- Statistical analysis (BER min/max/avg, threshold counts, training failures)
- Visualization (tables and heatmaps with configurable color schemes)
- Excel export with filtering and conditional formatting
- Interactive shell for exploratory analysis

Key Components:
    - DatabaseManager: Database schema management and operations
    - CSVIngester: Streaming CSV ingestion with filtering
    - QueryEngine: High-level query interface with lane selection
    - LaneSelector: Lane specification parser (e.g., "01:00.0/ETH07")
    - TableRenderer: Formatted table output
    - HeatMapRenderer: Color-coded heatmap visualization
    - ExcelExporter: Excel export with multi-sheet workbooks
    - AnalysisShell: Interactive REPL for exploratory analysis

Usage Examples:
    # Ingest CSV data
    from bh_glx_data.system_analysis import DatabaseManager, CSVIngester

    db = DatabaseManager("/path/to/analysis.db")
    db.initialize_schema()

    ingester = CSVIngester(db)
    result = ingester.ingest_directory("./data/")

    # Query BER statistics
    from bh_glx_data.system_analysis import QueryEngine, LaneSelector

    engine = QueryEngine(db)
    selector = LaneSelector.from_spec("01:00.0/ETH07")
    stats = engine.query_ber_statistics(selector, train_speeds=[200])

    # Visualize results
    from bh_glx_data.system_analysis import TableRenderer

    renderer = TableRenderer()
    print(renderer.render_ber_statistics(stats))
"""

from bh_glx_data.system_analysis.database import DatabaseManager, get_default_db_path
from bh_glx_data.system_analysis.ingestion import CSVIngester, IngestionResult, TestRecord
from bh_glx_data.system_analysis.query_engine import (
    BERStatistics,
    CustomThresholdCounts,
    LaneBERStats,
    LaneSelector,
    QueryEngine,
    ThresholdExceededCounts,
    TrainingFailureCounts,
)
from bh_glx_data.system_analysis.statistics import (
    calculate_lane_statistics,
    count_by_status,
    count_by_threshold,
)
from bh_glx_data.system_analysis.visualization import (
    BER_COLOR_SCHEMES,
    COUNT_COLOR_SCHEMES,
    ColorScheme,
    HeatMapRenderer,
    TableRenderer,
)

__all__ = [
    # Database
    "DatabaseManager",
    "get_default_db_path",
    # Ingestion
    "CSVIngester",
    "IngestionResult",
    "TestRecord",
    # Query Engine
    "QueryEngine",
    "LaneSelector",
    "BERStatistics",
    "LaneBERStats",
    "ThresholdExceededCounts",
    "CustomThresholdCounts",
    "TrainingFailureCounts",
    # Statistics
    "calculate_lane_statistics",
    "count_by_status",
    "count_by_threshold",
    # Visualization
    "TableRenderer",
    "HeatMapRenderer",
    "ColorScheme",
    "COUNT_COLOR_SCHEMES",
    "BER_COLOR_SCHEMES",
]

__version__ = "0.3.0"
