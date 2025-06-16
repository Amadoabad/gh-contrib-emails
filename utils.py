"""
Utility functions for GitHub Contributors Crawler
"""

import os
import logging
from datetime import datetime
from urllib.parse import urlparse
from config import LOGS_DIR, LOG_FORMAT, LOG_DATE_FORMAT, FAKE_EMAIL_PATTERNS


def setup_logging(log_level=logging.INFO):
    """Setup logging to both file and console"""
    # Create logs directory if it doesn't exist
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f'{LOGS_DIR}/github_crawler_{timestamp}.log'
    
    # Create logger
    logger = logging.getLogger('GitHubCrawler')
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    
    # File handler
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Log the setup
    logger.info(f"Logging initialized. Log file: {log_filename}")
    logger.info(f"Log level: {logging.getLevelName(log_level)}")
    
    return logger


def is_valid_github_url(url):
    """Check if URL is a valid GitHub repository URL"""
    if not url or url == 'nan':
        return False
    
    try:
        parsed = urlparse(url)
        if parsed.netloc != 'github.com':
            return False
        
        path_parts = parsed.path.strip('/').split('/')
        return len(path_parts) >= 2 and path_parts[0] and path_parts[1]
    except:
        return False


def is_valid_email(email):
    """Basic email validation"""
    if not email:
        return False
    
    # Skip obviously fake emails
    email_lower = email.lower()
    for pattern in FAKE_EMAIL_PATTERNS:
        if pattern in email_lower:
            return False
    
    # Basic format check
    return '@' in email and '.' in email.split('@')[-1]



def parse_repo_url(repo_url):
    """Parse strict GitHub repo URL and extract (owner, repo)"""
    parsed = urlparse(repo_url)
    
    if parsed.scheme not in ("http", "https"):
        return None, None
    if parsed.netloc != "github.com":
        return None, None

    parts = parsed.path.strip("/").split("/")
    
    # Must be exactly 2 parts: /owner/repo
    if len(parts) != 2:
        return None, None

    return parts[0], parts[1]


def clean_blog_url(blog_url):
    """Clean up blog URL by adding https if needed"""
    if blog_url and not blog_url.startswith('http'):
        return 'https://' + blog_url
    return blog_url


def export_links_to_file(links, filename='exported_links.txt'):
    """Export list of links to a text file"""
    if not links:
        logging.warning("No links to export.")
        return
    
    with open(filename, 'w', encoding='utf-8') as f:
        for link in links:
            f.write(link + '\n')
    
    logging.info(f"Exported {len(links)} links to {filename}")
    
def is_rate_limit_exceeded(response):
    """Check if the GitHub API response indicates a rate limit exceeded error."""
    if response.status_code == 403:
        try:
            data = response.json()
            return "API rate limit exceeded" in data.get("message", "")
        except ValueError:
            # Response is not JSON
            return False
    return False
