# Migration Guide: BH Galaxy Data Analysis Tool

**Version 0.1.0 Migration Guide**

This guide helps you migrate from the old script-based workflow to the new modern Python package with unified CLI commands.

---

## Table of Contents

- [Overview](#overview)
- [What's Changed](#whats-changed)
- [Installation](#installation)
- [Command Migration](#command-migration)
- [Programmatic API Migration](#programmatic-api-migration)
- [Configuration Migration](#configuration-migration)
- [Step-by-Step Migration](#step-by-step-migration)
- [Common Issues](#common-issues)
- [Deprecation Timeline](#deprecation-timeline)

---

## Overview

The BH Galaxy Data Analysis Tool has been modernized into a proper Python package with:
- ✅ Unified CLI with consistent interface
- ✅ Installable package (`pip install`)
- ✅ Improved error handling and logging
- ✅ Better configuration management
- ✅ Comprehensive test coverage
- ✅ Type safety with dataclasses

**Key Benefit:** Instead of running `python3 src/script.py`, you now use simple commands like `bh-jira-retrieve`.

---

## What's Changed

### Package Structure

**Before (v0.0.x):**
```
bh-glx-data/
├── src/
│   ├── jira_csv_retriever.py
│   ├── filter_failures.py
│   ├── excel_summary_generator.py
│   └── ...
```

**After (v0.1.0):**
```
bh-glx-data/
├── src/bh_glx_data/          # Proper package structure
│   ├── core/                 # Core abstractions
│   ├── jira_integration/     # Domain modules
│   ├── data_processing/
│   ├── excel_reporting/
│   ├── quanta_extraction/
│   └── hardware/
```

### CLI Interface

**Before:** Direct script execution
```bash
python3 src/jira_csv_retriever.py --tickets SYS-123
```

**After:** Unified CLI commands
```bash
bh-jira-retrieve --tickets SYS-123
```

### Import Paths

**Before:**
```python
from src.config import load_config
```

**After:**
```python
from bh_glx_data.core.config import ConfigManager
```

---

## Installation

### Old Way (No Installation Required)

Previously, you would:
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run scripts directly: `python3 src/script.py`

### New Way (Package Installation)

Now you install the package itself:

```bash
# Clone repository
git clone <repository-url>
cd bh-glx-data

# Install in development mode (recommended for contributors)
pip install -e ".[dev]"

# Or install for regular use
pip install .
```

**After installation, all commands are available in your PATH:**
```bash
bh-glx-data --help
bh-jira-retrieve --help
bh-filter-failures --help
# ... etc
```

---

## Command Migration

### Quick Reference Table

| Old Command | New Command | Notes |
|-------------|-------------|-------|
| `python3 src/jira_csv_retriever.py` | `bh-jira-retrieve` | Unchanged arguments |
| `python3 src/filter_failures.py` | `bh-filter-failures` | Unchanged arguments |
| `python3 src/excel_summary_generator.py` | `bh-generate-excel` | Unchanged arguments |
| `python3 src/extract_quanta_failures.py` | `bh-extract-quanta` | Unchanged arguments |
| `python3 src/platform_topology.py` | `bh-topology` | Unchanged arguments |

### Unified CLI Alternative

All commands are also available through the unified entry point:

```bash
# Old way (still works with deprecation warning)
python3 src/jira_csv_retriever.py --tickets SYS-123

# New way (option 1: direct command)
bh-jira-retrieve --tickets SYS-123

# New way (option 2: unified CLI)
bh-glx-data jira-retrieve --tickets SYS-123
```

### Detailed Command Examples

#### 1. Jira CSV Retrieval

**Before:**
```bash
python3 src/jira_csv_retriever.py --tickets SYS-123 SYS-456 --output-dir data/
```

**After:**
```bash
bh-jira-retrieve --tickets SYS-123 SYS-456 --output-dir data/
```

#### 2. Filter Failures

**Before:**
```bash
python3 src/filter_failures.py data_test_results.csv --output failures.csv
```

**After:**
```bash
bh-filter-failures data_test_results.csv --output failures.csv
```

#### 3. Generate Excel Reports

**Before:**
```bash
python3 src/excel_summary_generator.py --data-dir csv_data/ --output-dir summaries/
```

**After:**
```bash
bh-generate-excel --data-dir csv_data/ --output-dir summaries/
```

#### 4. Extract Quanta Failures

**Before:**
```bash
python3 src/extract_quanta_failures.py QC3_UBB_20260128.tar.gz --output-dir quanta/
```

**After:**
```bash
bh-extract-quanta QC3_UBB_20260128.tar.gz --output-dir quanta/
```

#### 5. Query Topology

**Before:**
```bash
python3 src/platform_topology.py 01:00.0 ETH07
```

**After:**
```bash
bh-topology 01:00.0 ETH07
```

---

## Programmatic API Migration

If you import and use these tools in your own Python scripts, the import paths have changed.

### Configuration Loading

**Before:**
```python
from src.config import load_config

config = load_config()
jira_config = config['jira']
```

**After:**
```python
from bh_glx_data.core.config import ConfigManager

config = ConfigManager.load()
jira_config = config.jira  # Now a typed dataclass
```

### Jira Integration

**Before:**
```python
from src.jira_csv_retriever import download_csv_attachments

download_csv_attachments(jira_client, ticket_key, output_dir)
```

**After:**
```python
from bh_glx_data.jira_integration.retriever import JiraCSVRetriever

retriever = JiraCSVRetriever(jira_client)
result = retriever.download_ticket_csvs(ticket_key, output_dir)
```

### Data Processing

**Before:**
```python
from src.filter_failures import filter_failures

filter_failures(input_file, output_file)
```

**After:**
```python
from bh_glx_data.data_processing.filter import filter_failures

result = filter_failures(input_file, output_file)
# result is now a FilterResult dataclass with metadata
```

### Excel Generation

**Before:**
```python
from src.excel_summary_generator import generate_excel_summary

generate_excel_summary(data_dir, output_dir)
```

**After:**
```python
from bh_glx_data.excel_reporting.generator import ExcelReportGenerator

generator = ExcelReportGenerator(template_path)
result = generator.generate_report(data_dir, output_dir)
```

### Platform Topology

**Before:**
```python
from src.platform_topology import get_connected_port, PLATFORM_TOPOLOGY

connection = get_connected_port("01:00.0", "ETH07")
```

**After:**
```python
from bh_glx_data.hardware.platform_topology import (
    get_connected_port,
    PLATFORM_TOPOLOGY
)

connection = get_connected_port("01:00.0", "ETH07")
# Returns Optional[Connection] tuple
```

### Data Models

**New feature in v0.1.0 - Type-safe data models:**

```python
from bh_glx_data.core.models import (
    TestResult,
    FailureRecord,
    SystemConfig,
    FilterResult
)

# All results now use dataclasses for type safety
result = filter_failures(input_file)
print(f"Found {result.failure_count} failures out of {result.total_rows} rows")
```

### Exception Handling

**New feature in v0.1.0 - Custom exception hierarchy:**

```python
from bh_glx_data.core.exceptions import (
    BHGlxDataError,
    ConfigurationError,
    DataProcessingError,
    JiraConnectionError
)

try:
    result = filter_failures(input_file)
except DataProcessingError as e:
    logger.error(f"Data processing failed: {e}")
except BHGlxDataError as e:
    logger.error(f"General error: {e}")
```

---

## Configuration Migration

### Configuration File Location

**Old behavior (v0.0.x):**
- `config.yaml` must be in current working directory
- `.env` must be in current working directory

**New behavior (v0.1.0):**

Configuration is now loaded from multiple sources in priority order:

1. **Command-line arguments** (highest priority)
2. **Environment variable** `BH_GLX_CONFIG=/path/to/config.yaml`
3. **User config**: `~/.config/bh-glx-data/config.yaml`
4. **Local config**: `./config.yaml`
5. **Built-in defaults** (lowest priority)

### Migration Steps

**Option 1: Keep local config (no changes needed)**
```bash
# Your existing config.yaml and .env still work
./config.yaml  # Still recognized
./.env         # Still recognized
```

**Option 2: Move to user config directory (recommended)**
```bash
# Create user config directory
mkdir -p ~/.config/bh-glx-data

# Move config files
cp config.yaml ~/.config/bh-glx-data/
cp .env ~/.config/bh-glx-data/

# Now config is available from any directory
cd /any/directory
bh-jira-retrieve  # Uses ~/.config/bh-glx-data/config.yaml
```

**Option 3: Use environment variable**
```bash
# Set config path
export BH_GLX_CONFIG=/path/to/my/config.yaml

# Or in your .bashrc/.zshrc
echo 'export BH_GLX_CONFIG=/path/to/config.yaml' >> ~/.bashrc
```

### Configuration Format

The `config.yaml` format is **unchanged**:

```yaml
# config.yaml (same format as before)
jira:
  server_url: https://your-jira.atlassian.net
  email: your-email@example.com
  api_key: your-api-token

tickets:
  - SYS-123
  - SYS-456

data:
  input_dir: csv_data
  output_dir: summaries
```

The `.env` format is also **unchanged**:

```env
# .env (same format as before)
JIRA_SERVER_URL=https://your-jira.atlassian.net
EMAIL=your-email@example.com
API_KEY=your-api-token
```

---

## Step-by-Step Migration

### For End Users (Running CLI Tools)

**Step 1: Install the package**
```bash
cd bh-glx-data
pip install -e .
```

**Step 2: Verify installation**
```bash
bh-glx-data --version
bh-jira-retrieve --help
```

**Step 3: Update your scripts/aliases**

If you have shell scripts or aliases:

```bash
# Old alias
alias download-jira="cd ~/bh-glx-data && python3 src/jira_csv_retriever.py"

# New alias
alias download-jira="bh-jira-retrieve"
```

**Step 4: (Optional) Move config to user directory**
```bash
mkdir -p ~/.config/bh-glx-data
cp config.yaml ~/.config/bh-glx-data/
cp .env ~/.config/bh-glx-data/
```

**Step 5: Test your workflows**
```bash
# Run your typical commands with new CLI
bh-jira-retrieve --tickets SYS-123
bh-filter-failures data_test_results.csv
bh-generate-excel
```

### For Developers (Using as Library)

**Step 1: Install with dev dependencies**
```bash
cd bh-glx-data
pip install -e ".[dev]"
```

**Step 2: Update import statements**

Search and replace in your codebase:
```bash
# Find old imports
grep -r "from src\." .
grep -r "import src\." .

# Replace with new imports (examples)
from src.config import load_config
→ from bh_glx_data.core.config import ConfigManager

from src.jira_csv_retriever import download_csv_attachments
→ from bh_glx_data.jira_integration.retriever import JiraCSVRetriever
```

**Step 3: Update function calls to use new APIs**

See [Programmatic API Migration](#programmatic-api-migration) section above.

**Step 4: Update exception handling**
```python
# Add proper exception handling
from bh_glx_data.core.exceptions import (
    BHGlxDataError,
    DataProcessingError
)

try:
    result = filter_failures(input_file)
except DataProcessingError as e:
    # Handle specific error
    pass
```

**Step 5: Run tests**
```bash
# Run test suite
pytest tests/

# Run your custom tests
python3 your_test_script.py
```

---

## Common Issues

### Issue 1: Command Not Found

**Problem:**
```bash
$ bh-jira-retrieve
-bash: bh-jira-retrieve: command not found
```

**Solution:**
The package is not installed. Install it:
```bash
cd bh-glx-data
pip install -e .
```

Or ensure you're in the correct virtual environment:
```bash
source .venv/bin/activate
pip install -e .
```

### Issue 2: Import Errors

**Problem:**
```python
ModuleNotFoundError: No module named 'src'
```

**Solution:**
Update import statements to use the new package:
```python
# Old
from src.config import load_config

# New
from bh_glx_data.core.config import ConfigManager
```

### Issue 3: Configuration Not Found

**Problem:**
```
ConfigurationError: config.yaml not found in search path
```

**Solution:**

Option 1 - Keep config in current directory:
```bash
# Ensure config.yaml is in current directory
ls config.yaml
```

Option 2 - Use user config directory:
```bash
mkdir -p ~/.config/bh-glx-data
cp config.yaml ~/.config/bh-glx-data/
```

Option 3 - Specify config path:
```bash
bh-jira-retrieve --config /path/to/config.yaml
```

### Issue 4: Old Scripts Still Warning

**Problem:**
```
DeprecationWarning: Direct script execution is deprecated.
Please use the new command: 'bh-jira-retrieve'
```

**Solution:**
This is expected! The old scripts still work but show warnings. Migrate to new commands:
```bash
# Instead of:
python3 src/jira_csv_retriever.py

# Use:
bh-jira-retrieve
```

### Issue 5: Different Working Directory Behavior

**Problem:**
Old scripts expected to run from repository root. New commands work from anywhere but use different config search paths.

**Solution:**
Either:
1. Move config to user directory (`~/.config/bh-glx-data/`)
2. Set `BH_GLX_CONFIG` environment variable
3. Use `--config` flag to specify config path

### Issue 6: Python Version Error

**Problem:**
```
ERROR: Package requires Python >=3.10 but you have 3.9.6
```

**Solution:**
The new package requires Python 3.10+. Options:
1. Upgrade Python to 3.10 or later
2. Use a Python 3.10+ virtual environment
3. Continue using old scripts (with deprecation warnings) until upgrade

---

## Deprecation Timeline

### Current: v0.1.0 (2026-03-05)

**Status:** Old scripts work with deprecation warnings

- ✅ All old scripts functional
- ⚠️ Deprecation warnings displayed
- ✅ New CLI commands available
- ✅ Both approaches supported

**Recommendation:** Start migrating to new commands

### Next Release: v0.2.0 (Est. Q2 2026)

**Status:** Old scripts marked deprecated

- ⚠️ Deprecation warnings more prominent
- ✅ Full backwards compatibility maintained
- 📖 Migration guide updated

**Recommendation:** Complete migration to new commands

### Future: v1.0.0 (Est. Q3-Q4 2026)

**Status:** Old scripts removed (breaking change)

- ❌ Old scripts removed from repository
- ✅ Only new CLI commands supported
- 📖 Comprehensive API documentation

**Action Required:** Must migrate before upgrading to v1.0.0

---

## Verification Checklist

Use this checklist to verify your migration:

### CLI Migration
- [ ] Package installed: `pip install -e .`
- [ ] Commands work: `bh-glx-data --help`
- [ ] All subcommands accessible:
  - [ ] `bh-jira-retrieve --help`
  - [ ] `bh-filter-failures --help`
  - [ ] `bh-generate-excel --help`
  - [ ] `bh-extract-quanta --help`
  - [ ] `bh-topology --help`
- [ ] Configuration loads correctly
- [ ] Test workflows execute successfully

### Programmatic Migration (if applicable)
- [ ] Import statements updated
- [ ] Function calls updated to new APIs
- [ ] Data models used for type safety
- [ ] Exception handling updated
- [ ] Tests pass with new imports

### Configuration Migration (optional)
- [ ] Config moved to `~/.config/bh-glx-data/` (optional)
- [ ] `BH_GLX_CONFIG` environment variable set (optional)
- [ ] Configuration loads from expected location

---

## Getting Help

If you encounter issues during migration:

1. **Check this guide** for common issues
2. **Review the README.md** for usage examples
3. **Run with verbose logging** for debugging:
   ```bash
   bh-glx-data --verbose <command> [options]
   ```
4. **Check command help**:
   ```bash
   bh-glx-data <command> --help
   ```
5. **Report issues** on the project's issue tracker

---

## Summary

**Key Changes:**
- ✅ Modern Python package with `pip install`
- ✅ Unified CLI with consistent interface
- ✅ Better configuration management
- ✅ Type-safe data models
- ✅ Comprehensive error handling
- ✅ Full test coverage

**Migration Path:**
1. Install package: `pip install -e .`
2. Replace script calls with CLI commands
3. Update import statements (if using programmatically)
4. (Optional) Move config to user directory
5. Test your workflows

**Backwards Compatibility:**
- Old scripts work until v1.0.0 (with warnings)
- Gradual migration is supported
- No breaking changes in v0.1.0

**Timeline:**
- v0.1.0 (current): Both approaches work
- v0.2.0 (Q2 2026): Migration encouraged
- v1.0.0 (Q3-Q4 2026): Old scripts removed

---

**Last Updated:** 2026-03-05
**Package Version:** 0.1.0
