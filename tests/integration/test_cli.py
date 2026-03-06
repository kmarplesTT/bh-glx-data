"""Integration tests for CLI interface."""

import subprocess
import sys
from pathlib import Path

import pytest


class TestUnifiedCLI:
    """Test the unified bh-glx-data CLI interface."""

    def test_cli_help(self):
        """Test that CLI help works."""
        # This tests the CLI module directly since entry points aren't installed in test env
        from bh_glx_data import cli

        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["bh-glx-data", "--help"]
            cli.main()

        # Help should exit with code 0
        assert exc_info.value.code == 0

    def test_cli_no_command(self):
        """Test that CLI without command shows help and exits."""
        from bh_glx_data import cli

        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["bh-glx-data"]
            cli.main()

        # Should exit with code 1 (error)
        assert exc_info.value.code == 1

    def test_cli_version(self):
        """Test that --version works."""
        from bh_glx_data import cli

        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["bh-glx-data", "--version"]
            cli.main()

        # Version should exit with code 0
        assert exc_info.value.code == 0

    def test_cli_invalid_command(self):
        """Test that invalid command shows help and exits."""
        from bh_glx_data import cli

        with pytest.raises(SystemExit):
            sys.argv = ["bh-glx-data", "invalid-command"]
            cli.main()


class TestCLISubcommands:
    """Test CLI subcommands routing."""

    def test_topology_subcommand(self):
        """Test topology subcommand help."""
        from bh_glx_data import cli

        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["bh-glx-data", "topology", "--help"]
            cli.main()

        assert exc_info.value.code == 0

    def test_filter_failures_subcommand_help(self):
        """Test filter-failures subcommand help."""
        from bh_glx_data import cli

        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["bh-glx-data", "filter-failures", "--help"]
            cli.main()

        assert exc_info.value.code == 0

    def test_analyze_failures_subcommand_help(self):
        """Test analyze-failures subcommand help."""
        from bh_glx_data import cli

        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["bh-glx-data", "analyze-failures", "--help"]
            cli.main()

        assert exc_info.value.code == 0


class TestDirectCommands:
    """Test direct command shortcuts work."""

    def test_topology_direct_help(self):
        """Test bh-topology command help."""
        from bh_glx_data.hardware import cli

        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["bh-topology", "--help"]
            cli.main()

        assert exc_info.value.code == 0

    def test_filter_failures_direct_help(self):
        """Test bh-filter-failures command help."""
        from bh_glx_data.data_processing import cli

        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["bh-filter-failures", "--help"]
            cli.main()

        assert exc_info.value.code == 0

    def test_analyze_failures_direct_help(self):
        """Test bh-analyze-failures command help."""
        from bh_glx_data.failure_analysis import cli

        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["bh-analyze-failures", "--help"]
            cli.main()

        assert exc_info.value.code == 0


class TestBackwardsCompatibility:
    """Test that old scripts still work with deprecation warnings."""

    def test_old_filter_failures_shows_warning(self):
        """Test that old filter_failures.py script shows deprecation warning."""
        import warnings

        # Run the old script and check for deprecation warning
        old_script = Path(__file__).parent.parent.parent / "src" / "filter_failures.py"

        if old_script.exists():
            # The script should show a deprecation warning when main() is called
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                # Import and try to call main (will fail due to missing args, but warning should trigger)
                sys.path.insert(0, str(old_script.parent))
                try:
                    import filter_failures

                    # Just importing won't trigger, need to call main
                    # We expect it to fail due to missing args, but we're testing the warning
                    try:
                        sys.argv = ["filter_failures.py", "--help"]
                        filter_failures.main()
                    except SystemExit:
                        pass
                except Exception:
                    pass
                finally:
                    sys.path.pop(0)

                # Check that at least one warning is a DeprecationWarning
                deprecation_warnings = [item for item in w if issubclass(item.category, DeprecationWarning)]
                assert len(deprecation_warnings) > 0, "Expected deprecation warning"
                assert "DEPRECATION WARNING" in str(deprecation_warnings[0].message)


class TestCLILogging:
    """Test CLI logging configuration."""

    def test_verbose_flag(self):
        """Test that --verbose flag works."""
        from bh_glx_data import cli

        # Test with verbose flag
        with pytest.raises(SystemExit):
            sys.argv = ["bh-glx-data", "--verbose", "--help"]
            cli.main()

    def test_log_level_flag(self):
        """Test that --log-level flag works."""
        from bh_glx_data import cli

        # Test with log-level flag
        with pytest.raises(SystemExit):
            sys.argv = ["bh-glx-data", "--log-level", "DEBUG", "--help"]
            cli.main()
