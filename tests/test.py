#
#Zur Zeit nur für "Ordnungen der Fakultäten und Einrichtungen", 
# da z.B. Studienordnungen, Prüfungsordnungen, ... bereits über 200 PDFs umfasst
#
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import re

def download_pdf(url, filepath):
    """Download a PDF file from url to filepath"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'_+', '_', filename)
    return filename[:240]  
def extract_data(url):
    document_data = []
    first_h3_text = None

    try:
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # extract 1. h3 Text
        first_h3_tag = soup.find('h3')
        if first_h3_tag:
            first_h3_text = first_h3_tag.get_text(strip=True)
        
        document_list_div = soup.find('div', id='document-list')
        
        # extract document titles and links
        if document_list_div:
            document_divs = document_list_div.find_all('div', class_='document')

            if not document_divs:
                print("Keine 'document' Elemente in der Hauptliste gefunden.")
            
            for doc_div in document_divs:
                title_tag = doc_div.find('p', class_='document__title')
                link_tag = doc_div.find('a', class_='document__download', href=True)
                
                if title_tag and link_tag:
                    title_text = title_tag.get_text(strip=True)
                
                    absolute_link = urljoin(url, link_tag['href'])
                    
                    document_data.append({
                        'titel': title_text,
                        'link': absolute_link
                    })
        
        # Important: Return the document_data even if empty
        return first_h3_text, document_data
                
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Zugriff auf die Webseite: {e}")
        return []
    
def collect_links_recursively(url, max_depth=3, current_depth=0, visited_urls=None, parent_h3=None):
    """
    Recursively collect all links and maintain hierarchy using h3 tags
    Returns: (document_urls, navigation_urls)
    Where document_urls is a list of tuples (url, h3_path)
    """
    if visited_urls is None:
        visited_urls = set()
    
    if current_depth >= max_depth or url in visited_urls:
        return [], []
    
    visited_urls.add(url)
    document_urls = []
    navigation_urls = []
    
    try:
        print(f"Checking depth {current_depth}: {url}")
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get current h3
        current_h3 = None
        h3_tag = soup.find('h3')
        if h3_tag:
            current_h3 = h3_tag.get_text(strip=True)
            print(f"Found headline: {current_h3}")
        
        # Build path
        h3_path = []
        if parent_h3:
            h3_path.extend(parent_h3)
        if current_h3:
            h3_path.append(current_h3)
        
        # Check if this page contains documents
        if soup.find('div', id='document-list'):
            document_urls.append((url, h3_path))
            print(f"✓ Found documents at: {url}")
            return document_urls, navigation_urls
        
        # Only look for links in categories-list
        categories_list = soup.find('ul', class_='categories-list')
        if categories_list:
            print(f"Found categories list at: {url}")
            links = categories_list.find_all('a', href=True)
            for link in links:
                full_url = urljoin(url, link['href'])
                if ('amb.uni-leipzig.de' in full_url and 
                    'bekanntmachungen' in full_url and 
                    full_url not in visited_urls):
                    
                    doc_urls, nav_urls = collect_links_recursively(
                        full_url, 
                        max_depth, 
                        current_depth + 1, 
                        visited_urls,
                        h3_path
                    )
                    document_urls.extend(doc_urls)
                    navigation_urls.extend(nav_urls)
        
        return document_urls, navigation_urls
                
    except requests.exceptions.RequestException as e:
        print(f"Error accessing {url}: {e}")
        return document_urls, navigation_urls

def main(start_url, max_depth=20):
    print(f"\nStarting recursive link collection from: {start_url}")
    
    # Get all document URLs with their h3 paths
    doc_urls_with_paths, nav_urls = collect_links_recursively(start_url, max_depth=max_depth)
    
    print("\n=== Results ===")
    print(f"Found {len(doc_urls_with_paths)} pages with documents")
    
    # Initialize hierarchical structure
    hierarchy = {}
    
    # Extract documents and maintain hierarchy
    for url, h3_path in doc_urls_with_paths:
        _, documents = extract_data(url)
        if documents:
            # Build nested dictionary structure
            current_level = hierarchy
            for h3 in h3_path[:-1]:  # All but the last h3
                if h3 not in current_level:
                    current_level[h3] = {"_docs": [], "_subdirs": {}}
                current_level = current_level[h3]["_subdirs"]
            
            # Add documents to the final level
            final_h3 = h3_path[-1] if h3_path else "Uncategorized"
            if final_h3 not in current_level:
                current_level[final_h3] = {"_docs": [], "_subdirs": {}}
            current_level[final_h3]["_docs"].extend(documents)
            
            print(f"✓ Added {len(documents)} documents to: {' > '.join(h3_path)}")

    # Create base directory
    base_dir = "Ordnungen der Fakultäten und Einrichtungen"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    # Function to process hierarchy
    def process_hierarchy(current_dict, current_path):
        download_stats = {"success": 0, "failed": 0}
        
        for name, content in current_dict.items():
            if name in ("_docs", "_subdirs"):
                continue
                
            # Create folder for current level
            folder_path = os.path.join(current_path, sanitize_filename(name))
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            
            # Download documents at this level
            if content["_docs"]:
                print(f"\nDownloading PDFs for: {name}")
                print("="*60)
                
                for doc in sorted(content["_docs"], key=lambda x: x['titel']):
                    filename = sanitize_filename(doc['titel']) + ".pdf"
                    filepath = os.path.join(folder_path, filename)
                    
                    print(f"Downloading: {doc['titel']}")
                    if download_pdf(doc['link'], filepath):
                        download_stats["success"] += 1
                    else:
                        download_stats["failed"] += 1
            
            # Process subdirectories
            sub_stats = process_hierarchy(content["_subdirs"], folder_path)
            download_stats["success"] += sub_stats["success"]
            download_stats["failed"] += sub_stats["failed"]
        
        return download_stats

    # Process the complete hierarchy
    stats = process_hierarchy(hierarchy, base_dir)
    
    # Print final statistics
    print("\n=== Download Statistics ===")
    print(f"Successfully downloaded: {stats['success']}")
    print(f"Failed downloads: {stats['failed']}")
    
    return hierarchy

if __name__ == "__main__":
    start_url = 'https://amb.uni-leipzig.de/startseite-bekanntmachungen.html?kat_id=2328'
    hierarchy = main(start_url)