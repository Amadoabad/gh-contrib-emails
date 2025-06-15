"""
Data processing and export functionality for GitHub Contributors Crawler
"""

import pandas as pd
import os
import logging
from datetime import datetime
from utils import is_valid_github_url, parse_repo_url
import re
class DataHandler:
    def __init__(self):
        self.logger = logging.getLogger('GitHubCrawler')

    def extract_repos_from_google_sheet(self, sheet_url, start_row, end_row):
        """Extract GitHub repository URLs from Google Sheet"""
        # Convert Google Sheets URL to CSV export URL
        if '/edit' in sheet_url:
            if '?gid=' in sheet_url or '#gid=' in sheet_url:
                csv_url = re.sub(r'/edit[?#]gid=', '/export?format=csv&gid=', sheet_url)
            else:
                csv_url = sheet_url.replace('/edit', '/export?format=csv')
        else:
            csv_url = sheet_url + '/export?format=csv'
        
        try:
            # Read the Google Sheet as CSV
            df = pd.read_csv(csv_url, header=None)
            self.logger.info(f"Successfully loaded Google Sheet with {len(df)} rows")
            
            # Extract URLs from the first column within the specified range
            # Convert to 0-based indexing (subtract 1 from row numbers)
            start_idx = max(0, start_row - 1)
            end_idx = min(len(df), end_row)
            
            urls = []
            for idx in range(start_idx, end_idx):
                if idx < len(df):
                    url = str(df.iloc[idx, 0]).strip()  # First column
                    if is_valid_github_url(url):
                        urls.append(url)
                        self.logger.debug(f"Row {idx + 1}: {url}")
                    else:
                        self.logger.warning(f"Row {idx + 1}: Invalid or empty URL - {url}")
            
            self.logger.info(f"Extracted {len(urls)} valid GitHub repository URLs")
            return urls
            
        except Exception as e:
            self.logger.error(f"Error reading Google Sheet: {e}")
            return []
    
    def get_list_of_repo_urls_from_readme(self, readme, owner, repo):
        """Get a list of repositories from provided repo"""
        urls = re.findall(r'https?://github\.com/[\w\.-]+/[\w\.-]+', readme)
        
        current_repo = f"{owner}/{repo}"
        external_urls = []
        
        for url in urls:
            sub_rebo_owner, sub_rebo_name = parse_repo_url(url)
            target_repo = f"{sub_rebo_owner}/{sub_rebo_name}"
            if target_repo and target_repo.lower() != current_repo:
                external_urls.append(url)
        
        return external_urls
    
    def save_to_excel(self, contributors, filename='github_contributors_results.xlsx', check_directory=None):
        """
        Save results to Excel file, checking for duplicates and against other workbooks in directory
        
        Args:
            contributors: List of contributor data
            filename: Target Excel filename
            check_directory: Directory path to check for existing Excel files (if None, only checks current file)
        """
        if not contributors:
            self.logger.warning("No contributors to save.")
            return
        
        # Create DataFrame from new contributors
        new_df = pd.DataFrame(contributors)
        
        # Step 1: Remove duplicates within the new data based on username
        initial_count = len(new_df)
        new_df = new_df.drop_duplicates(subset=['username'], keep='first')
        removed_internal = initial_count - len(new_df)
        
        if removed_internal > 0:
            self.logger.info(f"Removed {removed_internal} duplicate usernames from new data")
        
        # Step 2: Check against other workbooks in directory if provided
        existing_usernames = set()
        other_files_processed = 0
        
        if check_directory:
            if not os.path.exists(check_directory):
                self.logger.warning(f"Directory {check_directory} does not exist. Skipping external duplicate check.")
            else:
                self.logger.info(f"Scanning directory: {check_directory}")
                
                # Get all Excel files in the directory
                excel_files = []
                for file in os.listdir(check_directory):
                    if file.endswith(('.xlsx', '.xls')):
                        full_path = os.path.join(check_directory, file)
                        # Skip the current file we're about to save to
                        if os.path.abspath(full_path) != os.path.abspath(filename):
                            excel_files.append(full_path)
                
                self.logger.info(f"Found {len(excel_files)} Excel files to check for duplicates")
                
                for workbook_path in excel_files:
                    try:
                        other_df = pd.read_excel(workbook_path, sheet_name='All Contributors')
                        other_usernames = set(other_df['username'].dropna().astype(str))
                        existing_usernames.update(other_usernames)
                        other_files_processed += 1
                        self.logger.info(f"Loaded {len(other_usernames)} usernames from {os.path.basename(workbook_path)}")
                    except Exception as e:
                        self.logger.error(f"Error reading {os.path.basename(workbook_path)}: {e}")
                
                self.logger.info(f"Total unique usernames found across {other_files_processed} files: {len(existing_usernames)}")
        else:
            self.logger.info("No check directory provided. Only checking current file for duplicates.")
        
        # Step 3: Check if current file exists and load existing data
        if os.path.exists(filename):
            self.logger.info(f"File {filename} exists. Loading existing data...")
            
            try:
                # Read existing data
                existing_df = pd.read_excel(filename, sheet_name='All Contributors')
                self.logger.info(f"Found {len(existing_df)} existing contributors")
                
                # Add existing usernames to the set
                current_usernames = set(existing_df['username'].dropna().astype(str))
                existing_usernames.update(current_usernames)
                
            except Exception as e:
                self.logger.error(f"Error reading existing file: {e}")
                self.logger.info("Creating new file instead...")
                existing_df = pd.DataFrame()
        else:
            self.logger.info(f"Creating new file {filename}...")
            existing_df = pd.DataFrame()
        
        # Step 4: Filter out contributors that already exist in other workbooks or current file
        before_filter = len(new_df)
        new_usernames = set(new_df['username'].dropna().astype(str))
        duplicates_found = new_usernames.intersection(existing_usernames)
        
        if duplicates_found:
            self.logger.info(f"Found {len(duplicates_found)} usernames that already exist in other files")
            self.logger.debug(f"Duplicate usernames: {list(duplicates_found)[:10]}...")  # Show first 10
            # Filter out existing usernames
            new_df = new_df[~new_df['username'].isin(existing_usernames)]
        
        after_filter = len(new_df)
        removed_external = before_filter - after_filter
        
        if removed_external > 0:
            self.logger.info(f"Removed {removed_external} contributors that already exist in other files")
        
        # Step 5: Combine with existing data from current file
        if not existing_df.empty:
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
        
        # Final duplicate check (safety measure)
        before_final_dedup = len(combined_df)
        combined_df = combined_df.drop_duplicates(subset=['username'], keep='first')
        after_final_dedup = len(combined_df)
        
        if before_final_dedup > after_final_dedup:
            self.logger.info(f"Final cleanup: removed {before_final_dedup - after_final_dedup} duplicate entries")
        
        self.logger.info(f"Total contributors after all processing: {len(combined_df)}")
        self.logger.info(f"New unique contributors to be added: {len(new_df)}")
        
        # Step 6: Save to Excel with multiple sheets (all updated to reflect the cleaned data)
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Main sheet with all contributors
                combined_df.to_excel(writer, sheet_name='All Contributors', index=False)
                
                # Summary sheet by repository (updated to use cleaned data)
                if not combined_df.empty:
                    repo_summary = combined_df.groupby('repo_name').agg({
                        'username': 'count',
                        'repo_contributions': 'mean',
                        'yearly_contributions': 'mean'
                    }).round(2)
                    repo_summary.columns = ['Contributors Count', 'Avg Repo Contributions', 'Avg Yearly Contributions']
                    repo_summary.to_excel(writer, sheet_name='Repository Summary')
                
                # Sheet with just contact information (updated to use cleaned data)
                if not combined_df.empty:
                    contact_df = combined_df[['repo_name', 'username', 'name', 'email', 'commit_email', 'website', 'location', 'company', 'twitter']].copy()
                    
                    # Filter to only rows with some contact info
                    has_contact = (
                        (contact_df['email'].notna() & (contact_df['email'] != '')) |
                        (contact_df['commit_email'].notna() & (contact_df['commit_email'] != '')) |
                        (contact_df['website'].notna() & (contact_df['website'] != ''))
                    )
                    contact_df = contact_df[has_contact]
                    
                    contact_df.to_excel(writer, sheet_name='Contact Information', index=False)
                else:
                    # Create empty contact sheet if no data
                    contact_df = pd.DataFrame(columns=['repo_name', 'username', 'name', 'email', 'commit_email', 'website', 'location', 'company', 'twitter'])
                    contact_df.to_excel(writer, sheet_name='Contact Information', index=False)
                
                # Progress tracking sheet (updated with cleaning statistics)
                progress_data = {
                    'Last Updated': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                    'Total Contributors': [len(combined_df)],
                    'Total Repositories': [combined_df['repo_name'].nunique() if not combined_df.empty else 0],
                    'New Contributors Added': [len(new_df)],
                    'Contributors with Email': [len(contact_df) if not combined_df.empty else 0],
                    'Duplicates Removed (Internal)': [removed_internal],
                    'Duplicates Removed (External)': [removed_external],
                    'Excel Files Checked': [other_files_processed],
                    'Directory Scanned': [check_directory if check_directory else 'None']
                }
                progress_df = pd.DataFrame(progress_data)
                progress_df.to_excel(writer, sheet_name='Progress Log', index=False)
                
                # Duplicate tracking sheet (new sheet to track what was filtered out)
                if duplicates_found:
                    duplicate_data = {
                        'Duplicate Username': list(duplicates_found),
                        'Found In': ['Directory files/current file'] * len(duplicates_found),
                        'Date Detected': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')] * len(duplicates_found)
                    }
                    duplicate_df = pd.DataFrame(duplicate_data)
                    duplicate_df.to_excel(writer, sheet_name='Duplicates Filtered', index=False)
            
            self.logger.info(f"Results saved to {filename}")
            self.logger.info(f"Total contributors: {len(combined_df)}")
            self.logger.info(f"New unique contributors added: {len(new_df)}")
            self.logger.info(f"Contributors with contact info: {len(contact_df) if not combined_df.empty else 0}")
            self.logger.info(f"Excel files processed for duplicate check: {other_files_processed}")
            
        except Exception as e:
            self.logger.error(f"Error saving to Excel: {e}")
            # Fallback: save as CSV
            csv_filename = filename.replace('.xlsx', '_backup.csv')
            combined_df.to_csv(csv_filename, index=False)
            self.logger.info(f"Saved backup as CSV: {csv_filename}")

    # Example usage:
    # Check all Excel files in a specific directory
    # self.save_to_excel(contributors, 'new_contributors.xlsx', check_directory='./existing_data/')

    # Check all Excel files in current directory
    # self.save_to_excel(contributors, 'new_contributors.xlsx', check_directory='.')

    # Only check current file (original behavior)
    # self.save_to_excel(contributors, 'new_contributors.xlsx')