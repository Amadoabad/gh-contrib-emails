"""
Main GitHub Crawler class that orchestrates the contributor analysis process
"""

import time
import logging
from collections import Counter
from github_api import GitHubAPIClient
from data_handler import DataHandler
from utils import parse_repo_url, setup_logging, is_rate_limit_exceeded
from config import CONTRIBUTOR_DELAY, REPO_DELAY, DEFAULT_LOG_LEVEL
from scraper import get_pinned_repos
import re

class GitHubCrawler:
    def __init__(self, token=None, log_level=DEFAULT_LOG_LEVEL):
        self.token = token
        self.logger = setup_logging(log_level)
        self.api_client = GitHubAPIClient(token)
        self.data_handler = DataHandler()
    
    def filter_contributors_for_repo(self, repo_url, min_repo_contributions=100, min_yearly_contributions=400):
        """
        Filter contributors for a single repository based on criteria
        """
        # Parse repo URL to get owner and repo name
        owner, repo = parse_repo_url(repo_url)
        if not owner or not repo:
            self.logger.error(f"Invalid repo URL: {repo_url}")
            return []
        
        self.logger.info(f"Processing repository: {owner}/{repo}")
        
        try:
            # Get all contributors
            contributors = self.api_client.get_repo_contributors(owner, repo)
            self.logger.info(f"Found {len(contributors)} total contributors")
            
            # Filter by repo contributions first
            high_contributors = [c for c in contributors if c['contributions'] >= min_repo_contributions]
            self.logger.info(f"Contributors with ≥{min_repo_contributions} contributions: {len(high_contributors)}")
            
            qualified_contributors = []
            
            for contributor in high_contributors:
                username = contributor['login']
                
                yearly_contributions = self.api_client.get_user_contributions_last_year(username)
                
                self.logger.info(f"Checking {username}: {contributor['contributions']} repo contributions, {yearly_contributions} yearly contributions")
                
                if yearly_contributions >= min_yearly_contributions:
                    # Get detailed profile information
                    profile = self.api_client.get_user_profile(username)
                    
                    # Get commit email from patches
                    self.logger.debug(f"Getting commit email for {username}...")
                    commit_email = self.api_client.get_commit_email_from_repo(username, f"{owner}/{repo}")
                    
                    if commit_email is None:
                        self.logger.info(f"Trying to get the commit email from the user's pinned reois for {username}...")
                        pinned_repos = get_pinned_repos(username)    
                        for pinned_repo in pinned_repos:
                            commit_email = self.api_client._extract_email_from_repo_commits(username, pinned_repo)
                            if commit_email:
                                self.logger.info(f"Found commit email {commit_email} in pinned repo {pinned_repo} for {username}")
                                break
                        self.logger.warning(f"Couldn't find commit email for {username} in pinned repos")
                    
                    qualified_contributors.append({
                        'repo_url': repo_url,
                        'repo_name': f"{owner}/{repo}",
                        'username': username,
                        'repo_contributions': contributor['contributions'],
                        'yearly_contributions': yearly_contributions,
                        'profile_url': contributor['html_url'],
                        'name': profile.get('name', ''),
                        'email': profile.get('email', ''),
                        'commit_email': commit_email or '',
                        'website': profile.get('blog', ''),
                        'location': profile.get('location', ''),
                        'company': profile.get('company', ''),
                        'twitter': profile.get('twitter_username', ''),
                        'bio': profile.get('bio', ''),
                        'public_repos': profile.get('public_repos', 0),
                        'followers': profile.get('followers', 0),
                        'following': profile.get('following', 0),
                        'account_created': profile.get('created_at', '')
                    })
                
                # Rate limiting (GraphQL has different limits but being conservative)
                time.sleep(CONTRIBUTOR_DELAY)
            
            self.logger.info(f"Found {len(qualified_contributors)} qualified contributors for {owner}/{repo}")
            return qualified_contributors
            
        except Exception as e:
            self.logger.error(f"Error processing {repo_url}: {e}")
            return []
    
    def process_multiple_repos(self, repo_urls, min_stars, min_repo_contributions=100, min_yearly_contributions=400):
        """Process multiple repositories and return combined results"""
        all_contributors = []
        
        for i, repo_url in enumerate(repo_urls, 1):
            self.logger.info("=" * 80)
            self.logger.info(f"Processing repository {i}/{len(repo_urls)}: {repo_url}")
            self.logger.info("=" * 80)
            
            if min_stars:
                # Count stars for the repository
                owner, repo = parse_repo_url(repo_url)
                repo_stars = self.api_client.get_repo_stars(owner, repo)
                
                if not repo_stars: # Making sure the repo exists
                    continue
                
                if repo_stars < min_stars:
                    self.logger.info(f"Skipping {repo_url} due to insufficient stars (< {min_stars})")
                    continue
            
            contributors = self.filter_contributors_for_repo(
                repo_url, min_repo_contributions, min_yearly_contributions
            )
            all_contributors.extend(contributors)
            
            self.logger.info(f"Progress: {i}/{len(repo_urls)} repositories processed")
            
            # Small delay between repositories
            time.sleep(REPO_DELAY)
        
        return all_contributors
    
    def extract_repos(self, google_sheet_url, start_row, end_row, master_repo):
        """Extract GitHub repository URLs from Google Sheet"""
        
        if google_sheet_url is None and master_repo is None:
            self.logger.error("Please provide either a Google Sheet URL or a repository URL.")
        
        elif master_repo:    # Single repository URL provided
            self.logger.info(f"Using single repository URL: {master_repo}")
            owner, repo = parse_repo_url(master_repo)
            readme_content = self.api_client.get_repo_readme(owner, repo)
            while is_rate_limit_exceeded(readme_content):
                self.logger.warning(f"Rate limit exceeded while reading readme! Wait and we'll try again.")
                time.sleep(300)
                
            if not readme_content:
                self.logger.error(f"Failed to retrieve README content for {master_repo}")
                return
            
            return self.data_handler.get_list_of_repo_urls_from_readme(readme_content, owner, repo)
            
            
        else:            # Extract from Google Sheet
            self.logger.info(f"Using Google Sheet URL: {google_sheet_url}")
            return self.data_handler.extract_repos_from_google_sheet(google_sheet_url, start_row, end_row)

    def count_stars(self, repo_urls):
        """Count stars for a list of repository URLs"""
        star_counts = {}
        from tqdm import tqdm
        with tqdm(repo_urls, desc="Fetching stars") as pbar:
            for repo_url in pbar:
                owner, repo = parse_repo_url(repo_url)
                stars = self.api_client.get_repo_stars(owner, repo)
                if not stars:
                    continue
                star_counts[repo_url] = stars
                pbar.set_postfix({"repo": repo, "stars": stars})

        return star_counts

    
    def save_to_excel(self, contributors, filename='github_contributors_results.xlsx'):
        """Save results to Excel file"""
        return self.data_handler.save_to_excel(contributors, filename)

    