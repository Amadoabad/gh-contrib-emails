"""
GitHub API client for interacting with GitHub REST and GraphQL APIs
"""

import requests
import time
import logging
from datetime import datetime, timedelta, timezone
import base64
from config import (
    GITHUB_BASE_URL, GITHUB_GRAPHQL_URL, DEFAULT_HEADERS,
    RATE_LIMIT_DELAY
)

from utils import is_valid_email, clean_blog_url


class GitHubAPIClient:
    def __init__(self, token=None):
        self.token = token
        self.headers = DEFAULT_HEADERS.copy()
        if token:
            self.headers['Authorization'] = f'token {token}'
        
        self.base_url = GITHUB_BASE_URL
        self.graphql_url = GITHUB_GRAPHQL_URL
        self.logger = logging.getLogger('GitHubCrawler')
    
    def get_repo_contributors(self, owner, repo):
        """Get all contributors for a repository with their contribution counts"""
        contributors = []
        page = 1
        
        while True:
            url = f'{self.base_url}/repos/{owner}/{repo}/contributors'
            params = {'page': page, 'per_page': 100}
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                self.logger.error(f"Error fetching contributors for {owner}/{repo}: {response.status_code}")
                break
            
            data = response.json()
            if not data:  # No more contributors
                break
            
            contributors.extend(data)
            page += 1
            
            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)
        
        return contributors
    
    def get_user_contributions_last_year(self, username):
        """Get user's total contributions in the last year using GitHub GraphQL API"""
        if not self.token:
            self.logger.warning(f"No GitHub token provided. Using fallback method for {username}")
            return self.get_commits_from_events(username)
        
        try:
            # Calculate date range for last year
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=365)
            
            # GraphQL query to get contributions collection
            query = """
            query($username: String!, $from: DateTime!, $to: DateTime!) {
                user(login: $username) {
                    contributionsCollection(from: $from, to: $to) {
                        contributionCalendar {
                            totalContributions
                        }
                        totalCommitContributions
                        totalIssueContributions
                        totalPullRequestContributions
                        totalPullRequestReviewContributions
                        totalRepositoryContributions
                    }
                }
            }
            """
            
            variables = {
                "username": username,
                "from": start_date.isoformat(),
                "to": end_date.isoformat()
            }
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                self.graphql_url,
                json={'query': query, 'variables': variables},
                headers=headers
            )
            
            if response.status_code != 200:
                self.logger.error(f"GraphQL API error for {username}: {response.status_code}")
                return self.get_commits_from_events(username)  # Fallback
            
            data = response.json()
            
            if 'errors' in data:
                self.logger.error(f"GraphQL errors for {username}: {data['errors']}")
                return self.get_commits_from_events(username)  # Fallback
            
            user_data = data.get('data', {}).get('user')
            if not user_data:
                self.logger.warning(f"No user data found for {username}")
                return 0
            
            contributions_collection = user_data.get('contributionsCollection', {})
            
            # Get the total contributions (this is the number shown on the profile)
            total_contributions = contributions_collection.get('contributionCalendar', {}).get('totalContributions', 0)
            
            # Also get breakdown for debugging/info
            commit_contributions = contributions_collection.get('totalCommitContributions', 0)
            issue_contributions = contributions_collection.get('totalIssueContributions', 0)
            pr_contributions = contributions_collection.get('totalPullRequestContributions', 0)
            review_contributions = contributions_collection.get('totalPullRequestReviewContributions', 0)
            
            self.logger.debug(f"{username} contributions breakdown:")
            self.logger.debug(f"  Total: {total_contributions}")
            self.logger.debug(f"  Commits: {commit_contributions}, Issues: {issue_contributions}")
            self.logger.debug(f"  Pull Requests: {pr_contributions}, Reviews: {review_contributions}")
            
            return total_contributions
            
        except Exception as e:
            self.logger.error(f"Error fetching contributions for {username}: {e}")
            return self.get_commits_from_events(username)  # Fallback to old method
    
    def get_commits_from_events(self, username):
        """Fallback method: Get recent commit count from user events (last 90 days)"""
        self.logger.debug(f"Using fallback method for {username}")
        url = f'{self.base_url}/users/{username}/events'
        params = {'per_page': 100}
        
        total_commits = 0
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=365)        
        
        for page in range(1, 4):  # Check first 3 pages (300 events max)
            params['page'] = page
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                break
            
            events = response.json()
            if not events:
                break
            
            for event in events:
                if event['type'] == 'PushEvent':
                    event_date = datetime.fromisoformat(event['created_at'].replace('Z', '+00:00'))
                    if event_date >= cutoff_date:
                        # Count commits in this push event
                        commit_count = len(event.get('payload', {}).get('commits', []))
                        total_commits += commit_count
                    else:
                        # Events are chronological, so we can stop here
                        return total_commits
            
            time.sleep(RATE_LIMIT_DELAY)  # Rate limiting
        
        return total_commits
    
    def get_user_profile(self, username):
        """Get detailed user profile information"""
        url = f'{self.base_url}/users/{username}'
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            self.logger.error(f"Error fetching profile for {username}: {response.status_code}")
            return {}
        
        data = response.json()
        
        # Extract relevant profile information
        profile = {
            'email': data.get('email'),  # Public email (often None)
            'blog': clean_blog_url(data.get('blog')),    # Personal website/blog
            'location': data.get('location'),
            'name': data.get('name'),
            'bio': data.get('bio'),
            'company': data.get('company'),
            'twitter_username': data.get('twitter_username'),
            'public_repos': data.get('public_repos', 0),
            'followers': data.get('followers', 0),
            'following': data.get('following', 0),
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at')
        }
        
        return profile
    
    def get_commit_email_from_repo(self, username, src_repo):
        """Extract email from commit patches of user's own repositories"""
        try:
            # Get user's own repositories (sorted by creation date - oldest first)
            repos_url = f'{self.base_url}/users/{username}/repos'
            params = {
                'sort': 'created', 
                'direction': 'asc', 
                'per_page': 30,  # Get more repos to increase chances
                'type': 'all'  # Only repos owned by the user
            }
            
            response = requests.get(repos_url, headers=self.headers, params=params)
            if response.status_code != 200:
                self.logger.warning(f"Could not fetch repos for {username}")
                return None
            
            repos = response.json()
            
            if repos is not None and len(repos) != 0:
                
                self.logger.debug(f"Checking {len(repos)} repositories for {username}")
                
                # Try to find commits in the user's repositories, starting with oldest
                for i, repo in enumerate(repos):
                    repo_name = repo['full_name']
                    self.logger.debug(f"Checking repo {i+1}/{len(repos)}: {repo_name}")
                    
                    email = self._extract_email_from_repo_commits(username, repo_name)
                    if email:
                        self.logger.info(f"Found commit email for {username} in {repo_name}: {email}")
                        return email
                    
                    # If we've checked 10 repos without success, try some newer ones too
                    if i >= 9:
                        break
                        
                    time.sleep(0.2)  # Rate limiting
                
                # If no email found in old repos, try some recent repos
                self.logger.debug(f"No email found in old repos, trying recent repos for {username}")
                recent_params = {
                    'sort': 'updated', 
                    'direction': 'desc', 
                    'per_page': 15,
                    'type': 'owner'
                }
                
                response = requests.get(repos_url, headers=self.headers, params=recent_params)
                if response.status_code == 200:
                    recent_repos = response.json()
                    for i, repo in enumerate(recent_repos[:5]):  # Check 5 most recent
                        repo_name = repo['full_name']
                        self.logger.debug(f"Checking recent repo {i+1}/5: {repo_name}")
                        
                        email = self._extract_email_from_repo_commits(username, repo_name)
                        if email:
                            self.logger.info(f"Found commit email for {username} in {repo_name}: {email}")
                            return email
                        
                        time.sleep(0.2)
            
            else:
                self.logger.debug(f"No repositories found for {username}")
            
                
            self.logger.debug(f"No valid email found for {username} in any repository")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting commit email for {username}: {e}")
            return None
    
    def _extract_email_from_repo_commits(self, username, repo_name):
        """Extract email from commits in a specific repository"""
        try:
            # Get commits by this user in this repo
            commits_url = f'{self.base_url}/repos/{repo_name}/commits'
            params = {'author': username, 'per_page': 10}
            
            response = requests.get(commits_url, headers=self.headers, params=params)
            if response.status_code != 200:
                return None
            
            commits = response.json()
            if not commits:
                return None
            
            # Try to get email from the oldest commits first (more likely to be real email)
            for commit in reversed(commits):  # Reverse to start with oldest
                commit_sha = commit['sha']
                email = self._get_email_from_commit_api(repo_name, commit_sha)
                if email and is_valid_email(email):
                    return email
            
            return None
            
        except Exception as e:
            return None
    
    def _get_email_from_commit_api(self, repo_name, commit_sha):
        """Get email from a specific commit using the GitHub API"""
        try:
            # Construct API URL
            api_url = f'{self.base_url}/repos/{repo_name}/commits/{commit_sha}'

            response = requests.get(api_url, headers=self.headers)
            
            if response.status_code != 200:
                return None

            commit_data = response.json()
            
            # Get the author's email from the commit metadata
            email = commit_data.get('commit', {}).get('author', {}).get('email')
            return email

        except Exception as e:
            return None

    def get_repo_readme(self, owner, repo):
        """Get the README content of a repository"""
        readme_url = f'{self.base_url}/repos/{owner}/{repo}/readme'
        
        response = requests.get(readme_url, headers=self.headers)
        
        if response.status_code != 200:
            self.logger.error(f"Error fetching README for {owner}/{repo}: {response.status_code}")
            return None
        
        data = response.json()
        
        # Decode the content from base64
        encoded_content = data.get('content')
        if encoded_content:
            decoded_bytes = base64.b64decode(encoded_content)
            return decoded_bytes.decode('utf-8')
        return None

    def get_repo_stars(self, owner, repo):
        """Get the repo count of stars"""
        url = f"{self.base_url}/repos/{owner}/{repo}"
        response = requests.get(url, headers=self.headers)
        data = response.json()
        
        try:
            count = data['stargazers_count']
            return count
        except Exception as e:
            return
        