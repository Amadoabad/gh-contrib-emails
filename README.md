# GitHub Contributors Crawler

This project is a tool for extracting, filtering, and exporting information about contributors to GitHub repositories. It is designed to help analyze open source contributors based on repository activity and profile data.

## Features
- Extracts repository URLs from a Google Sheet or a repository README.
- Fetches contributors for each repository using the GitHub API.
- Filters contributors by minimum repository and yearly contribution counts.
- Collects additional profile and contact information for each contributor.
- Saves results to an Excel file with multiple summary sheets.
- Handles duplicate contributors across multiple runs and files.

## Main Components

- **main.py**: Entry point. Configures and runs the crawler, processes repositories, and saves results.
- **crawler.py**: Orchestrates the workflow. Handles repository extraction, contributor filtering, and result aggregation.
- **github_api.py**: Interacts with the GitHub REST and GraphQL APIs to fetch repository, contributor, and profile data.
- **data_handler.py**: Processes and exports contributor data, including duplicate checking and Excel export.
- **scraper.py**: Scrapes pinned repositories from a user's GitHub profile (used as a fallback for contact info).

## Usage
1. Configure your GitHub token and contribution thresholds in `config.py`.
2. Run `main.py` to start the process. You can specify a Google Sheet URL or a master repository URL.
3. The script will extract repository URLs, process contributors, and save the results to an Excel file.

## Environment Setup
1. (Optional) Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
2. Install dependencies from the requirements file:
    ```bash
    pip install -r requirements.txt
    ```

## Notes
- The tool uses both the GitHub REST and GraphQL APIs. A GitHub token is recommended for higher rate limits.
- Results are saved in `github_contributors_results.xlsx` by default.
- The code includes logging for progress and error tracking.

