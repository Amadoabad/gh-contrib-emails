"""
Main script to run the GitHub Contributors Crawler
"""

import logging
from collections import Counter
from crawler import GitHubCrawler
from config import (
    GITHUB_TOKEN,
    DEFAULT_MIN_REPO_CONTRIBUTIONS,
    DEFAULT_MIN_YEARLY_CONTRIBUTIONS
)


def main(google_sheet_url=None, start_row=1, end_row=100, master_repo=None, min_stars=0):
    """Main function to run the GitHub Contributors Crawler"""
    
    # Setup basic logging for main function
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('Main')

    logger.info("Configuration:")
    
        
    START_ROW = start_row or int(input("Enter start row number: "))
    END_ROW = end_row or int(input("Enter end row number: "))
    
    # Criteria configuration (use defaults from config or override here)
    MIN_REPO_CONTRIBUTIONS = DEFAULT_MIN_REPO_CONTRIBUTIONS
    MIN_YEARLY_CONTRIBUTIONS = DEFAULT_MIN_YEARLY_CONTRIBUTIONS
    
    logger.info(f"- Row range: {START_ROW} to {END_ROW}")
    logger.info(f"- Min repo contributions: {MIN_REPO_CONTRIBUTIONS}")
    logger.info(f"- Min yearly contributions: {MIN_YEARLY_CONTRIBUTIONS}")
    logger.info(f"- GitHub token: {'Provided' if GITHUB_TOKEN else 'Not provided (will use fallback method)'}")
    
    # Initialize crawler (this will setup its own detailed logging)
    crawler = GitHubCrawler(GITHUB_TOKEN, log_level=logging.INFO)
    
    # Extract repository URLs from Google Sheet
    crawler.logger.info("=" * 60)
    crawler.logger.info("EXTRACTING REPOSITORY URLS ")
    crawler.logger.info("=" * 60)
    
    repo_urls = crawler.extract_repos(google_sheet_url, START_ROW, END_ROW, master_repo)
    
    crawler.logger.info(f"Extracted {len(repo_urls)} repository URLs.")
    crawler.logger.info("Urls: " + ", ".join(repo_urls))
    
    if not repo_urls:
        crawler.logger.error("No valid repository URLs found. Exiting.")
        return

    # star_counts = crawler.count_stars(repo_urls)
    # # count the number of repositories with stars greater than min_stars
    # if min_stars > 0:
    #     repo_urls = [url for url, stars in star_counts.items() if stars >= min_stars]
    #     crawler.logger.info(f"Filtered repositories with stars >= {min_stars}: {len(repo_urls)}")
    # else:
    #     crawler.logger.info("No minimum stars filter applied.")
    # return
    
    # Process all repositories
    crawler.logger.info("=" * 60)
    crawler.logger.info("PROCESSING REPOSITORIES")
    crawler.logger.info("=" * 60)
    
    all_contributors = crawler.process_multiple_repos(
        repo_urls, MIN_REPO_CONTRIBUTIONS, MIN_YEARLY_CONTRIBUTIONS, min_stars
    )
    
    # Save results
    crawler.logger.info("=" * 60)
    crawler.logger.info("SAVING RESULTS")
    crawler.logger.info("=" * 60)
    
    crawler.save_to_excel(all_contributors)
    
    # Print summary
    if all_contributors:
        crawler.logger.info("SUMMARY:")
        crawler.logger.info(f"- Repositories processed: {len(repo_urls)}")
        crawler.logger.info(f"- Total qualified contributors: {len(all_contributors)}")
        crawler.logger.info(f"- Unique contributors: {len(set(c['username'] for c in all_contributors))}")
        
        # Show breakdown by repository
        repo_counts = Counter(c['repo_name'] for c in all_contributors)
        crawler.logger.info("Contributors by repository:")
        for repo, count in repo_counts.most_common():
            crawler.logger.info(f"  {repo}: {count} contributors")
    else:
        crawler.logger.warning("No qualified contributors found.")


if __name__ == "__main__":
    main(
        google_sheet_url= None,
        master_repo='https://github.com/fffaraz/awesome-cpp',
        min_stars=1000,
        start_row=1, end_row=100
    )
