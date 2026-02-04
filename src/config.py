"""
Configuration management
Loads environment variables from .env file using python-dotenv.
Loads ticket configuration from config.yaml file.
"""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Jira Configuration (from .env)
JIRA_SERVER_URL = os.getenv('JIRA_SERVER_URL')
EMAIL = os.getenv('EMAIL')
API_KEY = os.getenv('API_KEY')

# Load configuration from config.yaml
CONFIG_YAML_PATH = Path('config.yaml')
JIRA_TICKET_KEYS = []

if CONFIG_YAML_PATH.exists():
    try:
        with open(CONFIG_YAML_PATH, 'r') as f:
            config_data = yaml.safe_load(f)
            if config_data and 'tickets' in config_data:
                # Handle both list format and dict format (for future extensibility)
                tickets = config_data['tickets']
                if isinstance(tickets, list):
                    # Simple list format: ['SYS-123', 'SYS-456']
                    JIRA_TICKET_KEYS = [str(ticket).strip() for ticket in tickets if ticket]
                elif isinstance(tickets, dict):
                    # Future dict format: [{'key': 'SYS-123', ...}, ...]
                    # For now, just extract keys if needed
                    pass
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing config.yaml: {e}")
    except Exception as e:
        raise ValueError(f"Error reading config.yaml: {e}")
else:
    raise FileNotFoundError(
        "config.yaml not found. Please create config.yaml with a 'tickets' list. "
        "See README.md for instructions."
    )

# Output directory for downloaded CSV files
OUTPUT_DIR = Path('data')
OUTPUT_DIR.mkdir(exist_ok=True)


def validate_config():
    """
    Validate that all required configuration values are set.

    Returns:
        bool: True if all required values are set, False otherwise

    Raises:
        ValueError: If any required configuration is missing
    """
    missing = []

    if not JIRA_SERVER_URL:
        missing.append('JIRA_SERVER_URL')
    if not EMAIL:
        missing.append('EMAIL')
    if not API_KEY:
        missing.append('API_KEY')
    if missing:
        raise ValueError(
            f"Missing required configuration: {', '.join(missing)}. "
            f"Please set these in your .env file (copy from .env.example)."
        )

    if not JIRA_TICKET_KEYS:
        raise ValueError(
            "No tickets found in config.yaml. Please add at least one ticket key to the 'tickets' list."
        )

    return True
