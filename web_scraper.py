import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from tqdm import tqdm
import time

from config import config
from logging_config import get_logger

logger = get_logger(__name__)

class UniversityWebScraper:
    def __init__(self, download_dir: str = "data/downloaded_pdfs"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})

    def download_pdf(self, url: str, filepath: Path) -> bool:
        try:
            logger.debug(f"Downloading PDF: {url}")
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
                logger.warning(f"File may not be PDF: {url} (content-type: {content_type})")
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            if filepath.stat().st_size < 1024:
                logger.warning(f"Downloaded file is very small: {filepath}")
                return False
            logger.debug(f"Successfully downloaded: {filepath}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading {url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading {url}: {e}")
            return False

    def sanitize_filename(self, filename: str) -> str:
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'_+', '_', filename)
        return filename[:240].strip('_.')    

    def extract_documents_from_page(self, url: str) -> Tuple[Optional[str], List[Dict[str, str]]]:
        document_data = []
        page_title = None
        try:
            logger.debug(f"Extracting documents from: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            h3_tag = soup.find('h3')
            if h3_tag:
                page_title = h3_tag.get_text(strip=True)
            document_list_div = soup.find('div', id='document-list')
            if not document_list_div:
                logger.warning(f"No document-list found on: {url}")
                return page_title, []
            document_divs = document_list_div.find_all('div', class_='document')
            for doc_div in document_divs:
                title_tag = doc_div.find('p', class_='document__title')
                link_tag = doc_div.find('a', class_='document__download', href=True)
                if title_tag and link_tag:
                    title = title_tag.get_text(strip=True)
                    absolute_url = urljoin(url, link_tag['href'])
                    document_data.append({'title': title, 'url': absolute_url, 'filename': self.sanitize_filename(title) + '.pdf'})
            logger.info(f"Found {len(document_data)} documents on: {url}")
            return page_title, document_data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error accessing page {url}: {e}")
            return page_title, []
        except Exception as e:
            logger.error(f"Error parsing page {url}: {e}")
            return page_title, []

    def collect_document_pages_recursively(self, start_url: str, max_depth: int = 3, current_depth: int = 0, visited_urls: Optional[set] = None, parent_path: Optional[List[str]] = None) -> List[Tuple[str, List[str]]]:
        if visited_urls is None:
            visited_urls = set()
        if parent_path is None:
            parent_path = []
        if current_depth >= max_depth or start_url in visited_urls:
            return []
        visited_urls.add(start_url)
        document_pages = []
        try:
            logger.info(f"Exploring depth {current_depth}: {start_url}")
            response = self.session.get(start_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            current_title = None
            h3_tag = soup.find('h3')
            if h3_tag:
                current_title = h3_tag.get_text(strip=True)
            current_path = parent_path.copy()
            if current_title:
                current_path.append(current_title)
            if soup.find('div', id='document-list'):
                document_pages.append((start_url, current_path))
                logger.debug(f"Found document page: {' > '.join(current_path)}")
            categories_list = soup.find('ul', class_='categories-list')
            if categories_list and current_depth < max_depth:
                links = categories_list.find_all('a', href=True)
                for link in links:
                    full_url = urljoin(start_url, link['href'])
                    if ('amb.uni-leipzig.de' in full_url and 'bekanntmachungen' in full_url and full_url not in visited_urls):
                        time.sleep(0.5)
                        sub_pages = self.collect_document_pages_recursively(full_url, max_depth, current_depth + 1, visited_urls, current_path)
                        document_pages.extend(sub_pages)
            return document_pages
        except requests.exceptions.RequestException as e:
            logger.error(f"Error exploring {start_url}: {e}")
            return []

    def download_from_urls(self, start_urls: List[str], max_depth: int = 3) -> dict:
        stats = {'success': 0, 'failed': 0, 'skipped': 0}
        logger.info(f"Starting download from {len(start_urls)} URLs")
        all_document_pages = []
        for start_url in start_urls:
            logger.info(f"Collecting pages from: {start_url}")
            pages = self.collect_document_pages_recursively(start_url, max_depth)
            all_document_pages.extend(pages)
        logger.info(f"Found {len(all_document_pages)} document pages to process")
        for page_url, path_hierarchy in tqdm(all_document_pages, desc="Processing pages"):
            page_title, documents = self.extract_documents_from_page(page_url)
            if not documents:
                continue
            safe_path_parts = [self.sanitize_filename(part) for part in path_hierarchy]
            page_dir = self.download_dir
            for part in safe_path_parts:
                page_dir = page_dir / part
            for doc in documents:
                filepath = page_dir / doc['filename']
                if filepath.exists():
                    logger.debug(f"File already exists, skipping: {filepath}")
                    stats['skipped'] += 1
                    continue
                if self.download_pdf(doc['url'], filepath):
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
                time.sleep(0.2)
        return stats

def create_scraper(download_dir: str = None) -> UniversityWebScraper:
    if download_dir is None:
        download_dir = config.get('scraping.download_directory', 'data/downloaded_pdfs')
    return UniversityWebScraper(download_dir)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Download PDFs from University Leipzig')
    parser.add_argument('--urls', nargs='+', 
                        default=['https://amb.uni-leipzig.de/startseite-bekanntmachungen.html?kat_id=2001'],
                        help='URLs to scrape')
    parser.add_argument('--output-dir', default='data/downloaded_pdfs',
                        help='Output directory for downloaded PDFs')
    parser.add_argument('--max-depth', type=int, default=3,
                        help='Maximum recursion depth')
    args = parser.parse_args()
    from logging_config import setup_logging
    setup_logging(log_level='INFO')
    scraper = create_scraper(args.output_dir)
    stats = scraper.download_from_urls(args.urls, args.max_depth)
    print("\n📊 Download Statistics:")
    print(f"✅ Successful: {stats['success']}")
    print(f"❌ Failed: {stats['failed']}")
    print(f"⏭️  Skipped: {stats['skipped']}")
    print(f"📁 Output directory: {args.output_dir}")

if __name__ == "__main__":
    main()
