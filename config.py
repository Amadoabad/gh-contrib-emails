"""
Configuration settings for GitHub Contributors Crawler
"""

import logging
from dotenv import load_dotenv
import os 

load_dotenv()

# GitHub API Configuration
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']  # Replace with your GitHub personal access token
GITHUB_BASE_URL = 'https://api.github.com'
GITHUB_GRAPHQL_URL = 'https://api.github.com/graphql'

# Default filtering criteria
DEFAULT_MIN_REPO_CONTRIBUTIONS = 100
DEFAULT_MIN_YEARLY_CONTRIBUTIONS = 400

# Rate limiting settings
RATE_LIMIT_DELAY = 0.1  # seconds between API calls
CONTRIBUTOR_DELAY = 1.1  # seconds between processing contributors
REPO_DELAY = 1.0  # seconds between processing repositories

# Logging configuration
DEFAULT_LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# File paths
LOGS_DIR = 'logs'
DEFAULT_OUTPUT_FILE = 'github_contributors_results.xlsx'

# Email validation patterns (fake emails to skip)
FAKE_EMAIL_PATTERNS = [
    'noreply',
    'no-reply',
    'donotreply',
    'users.noreply.github.com',
    'localhost',
    'example.com',
    'test.com'
]

# API request headers
DEFAULT_HEADERS = {
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'GitHub-Contributors-Crawler'
}
