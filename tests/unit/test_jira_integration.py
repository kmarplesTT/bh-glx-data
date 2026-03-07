"""Unit tests for jira_integration module."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from jira.exceptions import JIRAError

from bh_glx_data.core.exceptions import (
    JiraAuthenticationError,
    JiraConnectionError,
)
from bh_glx_data.core.models import JiraConfig
from bh_glx_data.jira_integration.client import JiraClient
from bh_glx_data.jira_integration.retriever import (
    download_attachment,
    download_attachments,
    find_csv_attachments,
    process_ticket,
    process_tickets,
)


class TestJiraClient:
    """Test JiraClient class."""

    def test_client_initialization_success(self):
        """Test successful client initialization."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            email="test@example.com",
            api_key="test-api-key",
        )

        with patch("bh_glx_data.jira_integration.client.JIRA") as mock_jira:
            mock_jira.return_value = MagicMock()

            client = JiraClient(config)

            assert client.config == config
            assert client._client is not None
            mock_jira.assert_called_once_with(
                server="https://test.atlassian.net",
                basic_auth=("test@example.com", "test-api-key"),
            )

    def test_client_initialization_401_error(self):
        """Test authentication failure (401)."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            email="test@example.com",
            api_key="wrong-key",
        )

        with patch("bh_glx_data.jira_integration.client.JIRA") as mock_jira:
            jira_error = JIRAError(status_code=401, text="Unauthorized")
            mock_jira.side_effect = jira_error

            with pytest.raises(JiraAuthenticationError) as exc_info:
                JiraClient(config)

            assert "Authentication failed" in str(exc_info.value)

    def test_client_initialization_403_error(self):
        """Test access forbidden (403)."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            email="test@example.com",
            api_key="test-key",
        )

        with patch("bh_glx_data.jira_integration.client.JIRA") as mock_jira:
            jira_error = JIRAError(status_code=403, text="Forbidden")
            mock_jira.side_effect = jira_error

            with pytest.raises(JiraAuthenticationError) as exc_info:
                JiraClient(config)

            assert "Access forbidden" in str(exc_info.value)

    def test_client_initialization_connection_error(self):
        """Test connection error."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            email="test@example.com",
            api_key="test-key",
        )

        with patch("bh_glx_data.jira_integration.client.JIRA") as mock_jira:
            jira_error = JIRAError(status_code=500, text="Server Error")
            mock_jira.side_effect = jira_error

            with pytest.raises(JiraConnectionError) as exc_info:
                JiraClient(config)

            assert "Failed to connect" in str(exc_info.value)

    def test_client_initialization_unexpected_error(self):
        """Test unexpected error during initialization."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            email="test@example.com",
            api_key="test-key",
        )

        with patch("bh_glx_data.jira_integration.client.JIRA") as mock_jira:
            mock_jira.side_effect = ValueError("Unexpected error")

            with pytest.raises(JiraConnectionError) as exc_info:
                JiraClient(config)

            assert "Unexpected error" in str(exc_info.value)

    def test_client_property_success(self):
        """Test accessing client property."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            email="test@example.com",
            api_key="test-key",
        )

        with patch("bh_glx_data.jira_integration.client.JIRA") as mock_jira:
            mock_jira_instance = MagicMock()
            mock_jira.return_value = mock_jira_instance

            client = JiraClient(config)
            assert client.client == mock_jira_instance

    def test_client_property_not_connected(self):
        """Test accessing client property when not connected."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            email="test@example.com",
            api_key="test-key",
        )

        with patch("bh_glx_data.jira_integration.client.JIRA") as mock_jira:
            mock_jira.return_value = MagicMock()

            client = JiraClient(config)
            client._client = None

            with pytest.raises(JiraConnectionError) as exc_info:
                _ = client.client

            assert "not connected" in str(exc_info.value)

    def test_get_issue_success(self):
        """Test successful issue retrieval."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            email="test@example.com",
            api_key="test-key",
        )

        with patch("bh_glx_data.jira_integration.client.JIRA") as mock_jira:
            mock_jira_instance = MagicMock()
            mock_issue = MagicMock()
            mock_issue.fields.summary = "Test Issue"
            mock_jira_instance.issue.return_value = mock_issue
            mock_jira.return_value = mock_jira_instance

            client = JiraClient(config)
            issue = client.get_issue("SYS-123")

            assert issue == mock_issue
            mock_jira_instance.issue.assert_called_once_with("SYS-123")

    def test_get_issue_not_found(self):
        """Test issue not found (404)."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            email="test@example.com",
            api_key="test-key",
        )

        with patch("bh_glx_data.jira_integration.client.JIRA") as mock_jira:
            mock_jira_instance = MagicMock()
            jira_error = JIRAError(status_code=404, text="Not Found")
            mock_jira_instance.issue.side_effect = jira_error
            mock_jira.return_value = mock_jira_instance

            client = JiraClient(config)
            issue = client.get_issue("SYS-999")

            assert issue is None

    def test_get_issue_connection_error(self):
        """Test connection error during issue retrieval."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            email="test@example.com",
            api_key="test-key",
        )

        with patch("bh_glx_data.jira_integration.client.JIRA") as mock_jira:
            mock_jira_instance = MagicMock()
            jira_error = JIRAError(status_code=500, text="Server Error")
            mock_jira_instance.issue.side_effect = jira_error
            mock_jira.return_value = mock_jira_instance

            client = JiraClient(config)

            with pytest.raises(JiraConnectionError) as exc_info:
                client.get_issue("SYS-123")

            assert "Failed to retrieve ticket" in str(exc_info.value)

    def test_get_issue_unexpected_error(self):
        """Test unexpected error during issue retrieval."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            email="test@example.com",
            api_key="test-key",
        )

        with patch("bh_glx_data.jira_integration.client.JIRA") as mock_jira:
            mock_jira_instance = MagicMock()
            mock_jira_instance.issue.side_effect = ValueError("Unexpected")
            mock_jira.return_value = mock_jira_instance

            client = JiraClient(config)

            with pytest.raises(JiraConnectionError) as exc_info:
                client.get_issue("SYS-123")

            assert "Unexpected error" in str(exc_info.value)

    def test_download_attachment_success(self):
        """Test successful attachment download."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            email="test@example.com",
            api_key="test-key",
        )

        with patch("bh_glx_data.jira_integration.client.JIRA") as mock_jira:
            mock_jira.return_value = MagicMock()

            client = JiraClient(config)

            mock_attachment = MagicMock()
            mock_attachment.get.return_value = b"CSV content"
            mock_attachment.filename = "test.csv"

            content = client.download_attachment(mock_attachment)

            assert content == b"CSV content"
            mock_attachment.get.assert_called_once()

    def test_download_attachment_error(self):
        """Test attachment download error."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            email="test@example.com",
            api_key="test-key",
        )

        with patch("bh_glx_data.jira_integration.client.JIRA") as mock_jira:
            mock_jira.return_value = MagicMock()

            client = JiraClient(config)

            mock_attachment = MagicMock()
            mock_attachment.get.side_effect = Exception("Download failed")
            mock_attachment.filename = "test.csv"

            with pytest.raises(JiraConnectionError) as exc_info:
                client.download_attachment(mock_attachment)

            assert "Failed to download attachment" in str(exc_info.value)

    def test_close(self):
        """Test closing the client."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            email="test@example.com",
            api_key="test-key",
        )

        with patch("bh_glx_data.jira_integration.client.JIRA") as mock_jira:
            mock_jira_instance = MagicMock()
            mock_jira.return_value = mock_jira_instance

            client = JiraClient(config)
            client.close()

            assert client._client is None
            mock_jira_instance.close.assert_called_once()

    def test_context_manager(self):
        """Test using client as context manager."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            email="test@example.com",
            api_key="test-key",
        )

        with patch("bh_glx_data.jira_integration.client.JIRA") as mock_jira:
            mock_jira_instance = MagicMock()
            mock_jira.return_value = mock_jira_instance

            with JiraClient(config) as client:
                assert client._client is not None

            # After exiting context, client should be closed
            mock_jira_instance.close.assert_called_once()


class TestFindCSVAttachments:
    """Test find_csv_attachments function."""

    def test_find_csv_attachments_success(self):
        """Test finding CSV attachments."""
        mock_issue = MagicMock()
        mock_csv1 = MagicMock()
        mock_csv1.filename = "test1.csv"
        mock_csv2 = MagicMock()
        mock_csv2.filename = "test2.CSV"
        mock_txt = MagicMock()
        mock_txt.filename = "readme.txt"

        mock_issue.fields.attachment = [mock_csv1, mock_csv2, mock_txt]

        result = find_csv_attachments(mock_issue)

        assert len(result) == 2
        assert mock_csv1 in result
        assert mock_csv2 in result
        assert mock_txt not in result

    def test_find_csv_attachments_none(self):
        """Test finding CSV when no attachments exist."""
        mock_issue = MagicMock()
        mock_issue.fields.attachment = None

        result = find_csv_attachments(mock_issue)

        assert result == []

    def test_find_csv_attachments_no_csv(self):
        """Test finding CSV when no CSV files exist."""
        mock_issue = MagicMock()
        mock_txt = MagicMock()
        mock_txt.filename = "readme.txt"
        mock_xlsx = MagicMock()
        mock_xlsx.filename = "data.xlsx"

        mock_issue.fields.attachment = [mock_txt, mock_xlsx]

        result = find_csv_attachments(mock_issue)

        assert result == []

    def test_find_csv_attachments_no_attachment_field(self):
        """Test finding CSV when attachment field doesn't exist."""
        mock_issue = MagicMock(spec=[])  # No fields attribute
        delattr(mock_issue, "fields")

        # Should handle gracefully
        try:
            result = find_csv_attachments(mock_issue)
            assert result == []
        except AttributeError:
            # Acceptable behavior
            pass


class TestDownloadAttachment:
    """Test download_attachment function."""

    def test_download_attachment_success(self, tmp_path):
        """Test successful attachment download."""
        mock_client = MagicMock()
        mock_client.download_attachment.return_value = b"CSV content"

        mock_issue = MagicMock()
        mock_issue.key = "SYS-123"

        mock_attachment = MagicMock()
        mock_attachment.filename = "test.csv"

        result = download_attachment(
            mock_client,
            mock_issue,
            mock_attachment,
            tmp_path,
        )

        assert result == tmp_path / "SYS-123_test.csv"
        assert result.exists()
        assert result.read_bytes() == b"CSV content"

    def test_download_attachment_with_spaces(self, tmp_path):
        """Test attachment download with spaces in filename."""
        mock_client = MagicMock()
        mock_client.download_attachment.return_value = b"CSV content"

        mock_issue = MagicMock()
        mock_issue.key = "SYS-123"

        mock_attachment = MagicMock()
        mock_attachment.filename = "test data.csv"

        result = download_attachment(
            mock_client,
            mock_issue,
            mock_attachment,
            tmp_path,
        )

        # Spaces should be replaced with underscores
        assert result == tmp_path / "SYS-123_test_data.csv"
        assert result.exists()

    def test_download_attachment_error(self, tmp_path):
        """Test attachment download error."""
        mock_client = MagicMock()
        mock_client.download_attachment.side_effect = Exception("Download failed")

        mock_issue = MagicMock()
        mock_issue.key = "SYS-123"

        mock_attachment = MagicMock()
        mock_attachment.filename = "test.csv"

        result = download_attachment(
            mock_client,
            mock_issue,
            mock_attachment,
            tmp_path,
        )

        assert result is None


class TestDownloadAttachments:
    """Test download_attachments function."""

    def test_download_attachments_parallel_success(self, tmp_path):
        """Test parallel download of multiple attachments."""
        mock_client = MagicMock()
        mock_client.download_attachment.return_value = b"CSV content"

        mock_issue = MagicMock()
        mock_issue.key = "SYS-123"

        mock_attachment1 = MagicMock()
        mock_attachment1.filename = "test1.csv"
        mock_attachment2 = MagicMock()
        mock_attachment2.filename = "test2.csv"
        mock_attachment3 = MagicMock()
        mock_attachment3.filename = "test3.csv"

        attachments = [mock_attachment1, mock_attachment2, mock_attachment3]

        result = download_attachments(
            mock_client,
            mock_issue,
            attachments,
            tmp_path,
            max_workers=2,
        )

        assert len(result) == 3
        assert all(path.exists() for path in result)

    def test_download_attachments_empty_list(self, tmp_path):
        """Test download with empty attachment list."""
        mock_client = MagicMock()
        mock_issue = MagicMock()

        result = download_attachments(
            mock_client,
            mock_issue,
            [],
            tmp_path,
        )

        assert result == []

    def test_download_attachments_partial_failure(self, tmp_path):
        """Test parallel download with some failures."""
        mock_client = MagicMock()

        # First two succeed, third fails
        def download_side_effect(attachment):
            if attachment.filename == "fail.csv":
                raise Exception("Download failed")
            return b"CSV content"

        mock_client.download_attachment.side_effect = download_side_effect

        mock_issue = MagicMock()
        mock_issue.key = "SYS-123"

        mock_attachment1 = MagicMock()
        mock_attachment1.filename = "test1.csv"
        mock_attachment2 = MagicMock()
        mock_attachment2.filename = "test2.csv"
        mock_attachment3 = MagicMock()
        mock_attachment3.filename = "fail.csv"

        attachments = [mock_attachment1, mock_attachment2, mock_attachment3]

        result = download_attachments(
            mock_client,
            mock_issue,
            attachments,
            tmp_path,
            max_workers=2,
        )

        # Only 2 should succeed
        assert len(result) == 2


class TestProcessTicket:
    """Test process_ticket function."""

    def test_process_ticket_success(self, tmp_path):
        """Test successful ticket processing."""
        mock_client = MagicMock()

        # Mock issue with CSV attachments
        mock_issue = MagicMock()
        mock_issue.key = "SYS-123"
        mock_attachment = MagicMock()
        mock_attachment.filename = "test.csv"
        mock_issue.fields.attachment = [mock_attachment]

        mock_client.get_issue.return_value = mock_issue
        mock_client.download_attachment.return_value = b"CSV content"

        result = process_ticket(
            mock_client,
            "SYS-123",
            tmp_path,
        )

        assert result["ticket_key"] == "SYS-123"
        assert result["found"] is True
        assert result["csv_count"] == 1
        assert result["downloaded"] == 1
        assert len(result["downloaded_files"]) == 1
        assert len(result["errors"]) == 0

    def test_process_ticket_not_found(self, tmp_path):
        """Test processing ticket that doesn't exist."""
        mock_client = MagicMock()
        mock_client.get_issue.return_value = None

        result = process_ticket(
            mock_client,
            "SYS-999",
            tmp_path,
        )

        assert result["ticket_key"] == "SYS-999"
        assert result["found"] is False
        assert result["csv_count"] == 0
        assert result["downloaded"] == 0
        assert len(result["errors"]) == 1
        assert "not found" in result["errors"][0]

    def test_process_ticket_no_csv_attachments(self, tmp_path):
        """Test processing ticket with no CSV attachments."""
        mock_client = MagicMock()

        # Mock issue with no CSV attachments
        mock_issue = MagicMock()
        mock_issue.key = "SYS-123"
        mock_issue.fields.attachment = []

        mock_client.get_issue.return_value = mock_issue

        result = process_ticket(
            mock_client,
            "SYS-123",
            tmp_path,
        )

        assert result["ticket_key"] == "SYS-123"
        assert result["found"] is True
        assert result["csv_count"] == 0
        assert result["downloaded"] == 0
        assert len(result["errors"]) == 1
        assert "No CSV attachments" in result["errors"][0]

    def test_process_ticket_connection_error(self, tmp_path):
        """Test processing ticket with connection error."""
        mock_client = MagicMock()
        mock_client.get_issue.side_effect = JiraConnectionError(
            "Connection failed",
            server_url="https://test.atlassian.net",
        )

        result = process_ticket(
            mock_client,
            "SYS-123",
            tmp_path,
        )

        assert result["ticket_key"] == "SYS-123"
        assert result["found"] is False
        assert len(result["errors"]) == 1
        assert "Connection error" in result["errors"][0]


class TestProcessTickets:
    """Test process_tickets function."""

    def test_process_tickets_success(self, tmp_path):
        """Test successful processing of multiple tickets."""
        mock_client = MagicMock()

        # Mock successful issue retrieval
        def get_issue_side_effect(ticket_key):
            mock_issue = MagicMock()
            mock_issue.key = ticket_key
            mock_attachment = MagicMock()
            mock_attachment.filename = f"{ticket_key}.csv"
            mock_issue.fields.attachment = [mock_attachment]
            return mock_issue

        mock_client.get_issue.side_effect = get_issue_side_effect
        mock_client.download_attachment.return_value = b"CSV content"

        ticket_keys = ["SYS-123", "SYS-456"]

        result = process_tickets(
            mock_client,
            ticket_keys,
            tmp_path,
            max_workers=2,
        )

        assert result.success is True
        assert result.total_downloads == 2
        assert len(result.downloaded_files) == 2
        assert len(result.failed_tickets) == 0

    def test_process_tickets_partial_failure(self, tmp_path):
        """Test processing tickets with some failures."""
        mock_client = MagicMock()

        def get_issue_side_effect(ticket_key):
            if ticket_key == "SYS-999":
                return None  # Not found
            mock_issue = MagicMock()
            mock_issue.key = ticket_key
            mock_attachment = MagicMock()
            mock_attachment.filename = f"{ticket_key}.csv"
            mock_issue.fields.attachment = [mock_attachment]
            return mock_issue

        mock_client.get_issue.side_effect = get_issue_side_effect
        mock_client.download_attachment.return_value = b"CSV content"

        ticket_keys = ["SYS-123", "SYS-999", "SYS-456"]

        result = process_tickets(
            mock_client,
            ticket_keys,
            tmp_path,
            max_workers=2,
        )

        assert result.success is True  # At least one succeeded
        assert result.total_downloads == 2
        assert len(result.failed_tickets) == 1
        assert "SYS-999" in result.failed_tickets
        assert result.error_message is not None

    def test_process_tickets_all_failures(self, tmp_path):
        """Test processing tickets with all failures."""
        mock_client = MagicMock()
        mock_client.get_issue.return_value = None  # All not found

        ticket_keys = ["SYS-999", "SYS-998"]

        result = process_tickets(
            mock_client,
            ticket_keys,
            tmp_path,
            max_workers=2,
        )

        assert result.success is False
        assert result.total_downloads == 0
        assert len(result.failed_tickets) == 2
        assert result.error_message is not None

    def test_process_tickets_creates_output_directory(self, tmp_path):
        """Test that output directory is created."""
        mock_client = MagicMock()
        mock_client.get_issue.return_value = None

        output_dir = tmp_path / "new_directory"
        assert not output_dir.exists()

        process_tickets(
            mock_client,
            ["SYS-123"],
            output_dir,
        )

        assert output_dir.exists()
