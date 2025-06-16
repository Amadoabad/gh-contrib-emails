import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from utils import is_rate_limit_exceeded

def get_pinned_repos(username):
    """
    Scrapes GitHub user's pinned repositories and returns their full names (owner/repo format).
    
    Args:
        username (str): GitHub username
        
    Returns:
        list: List of pinned repository names in 'owner/repo' format
        
    Raises:
        requests.RequestException: If there's an issue with the HTTP request
        ValueError: If the user doesn't exist or has no pinned repos
    """
    
    # GitHub profile URL
    profile_url = f"https://github.com/{username}"
    
    # Headers to mimic a real browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Make request to GitHub profile
        while True:
            response = requests.get(profile_url, headers=headers)
        
            if is_rate_limit_exceeded(response):
                print(f"Rate limit exceeded while getting repo contributors! Wait and we'll try again.")
                time.sleep(300)
            else:
                break
            
        
        response.raise_for_status()
        
        # Check if user exists (GitHub returns 404 for non-existent users)
        if response.status_code == 404:
            raise ValueError(f"GitHub user '{username}' not found")
            
        # Parse HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find pinned repository containers
        # GitHub uses different selectors for pinned repos
        pinned_repos = []
        
        # Look for pinned repositories section
        pinned_items = soup.find_all('div', {'class': lambda x: x and 'pinned-item-list-item' in x})
        
        if not pinned_items:
            # Alternative selector pattern
            pinned_items = soup.find_all('article', {'class': lambda x: x and 'Box-row' in x})
        
        if not pinned_items:
            # Try another common pattern
            pinned_section = soup.find('div', {'class': lambda x: x and 'js-pinned-items-reorder-container' in x})
            if pinned_section:
                pinned_items = pinned_section.find_all('div', {'class': lambda x: x and 'Box-row' in x})
        
        # Extract repository names
        for item in pinned_items:
            # Look for repository link
            repo_link = item.find('a', {'class': lambda x: x and 'text-bold' in x})
            if not repo_link:
                repo_link = item.find('a', href=lambda x: x and '/tree/' not in x and '/blob/' not in x and '/' in x)
            
            if repo_link and repo_link.get('href'):
                # Extract full repository name (owner/repo) from the URL
                href = repo_link.get('href')
                if href.startswith('/'):
                    # Remove leading slash and extract owner/repo
                    path_parts = href[1:].split('/')
                    if len(path_parts) >= 2:
                        repo_full_name = f"{path_parts[0]}/{path_parts[1]}"
                        if repo_full_name and repo_full_name not in pinned_repos:
                            pinned_repos.append(repo_full_name)
        
        # If no pinned repos found, try alternative approach
        if not pinned_repos:
            # Look for any repository links in the profile that might be pinned
            repo_links = soup.find_all('a', href=lambda x: x and '/' in x and len(x.split('/')) >= 3)
            
            for link in repo_links[:6]:  # Limit to first 6 as GitHub shows max 6 pinned repos
                href = link.get('href')
                if href and href.startswith('/') and not any(skip in href for skip in ['/tree/', '/blob/', '/issues', '/pulls', '/wiki', '/settings']):
                    # Extract owner/repo from URL path
                    path_parts = href[1:].split('/')
                    if len(path_parts) >= 2:
                        repo_full_name = f"{path_parts[0]}/{path_parts[1]}"
                        if repo_full_name and repo_full_name not in pinned_repos:
                            pinned_repos.append(repo_full_name)
        
        return pinned_repos
        
    except requests.RequestException as e:
        raise requests.RequestException(f"Error fetching GitHub profile: {e}")


if __name__ == "__main__":
    # Example usage
    username = input("Enter GitHub username: ")
    try:
        pinned_repos = get_pinned_repos(username)
        if pinned_repos:
            print(f"Pinned repositories for {username}:")
            for repo in pinned_repos:
                print(repo)
        else:
            print(f"No pinned repositories found for {username}.")
    except ValueError as ve:
        print(ve)
    except requests.RequestException as re:
        print(re)
