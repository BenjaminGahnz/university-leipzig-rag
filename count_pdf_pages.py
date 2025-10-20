import argparse
import sys
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from tqdm import tqdm


project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from logging_config import get_logger, setup_logging


setup_logging(log_level="INFO")
logger = get_logger(__name__)


def count_pages_in_directory(directory: Path) -> tuple[int, int, int]:

    if not directory.is_dir():
        logger.error(f"Directory not found: {directory}")
        return 0, 0, 0

    pdf_files = list(directory.rglob("*.pdf"))
    total_pages = 0
    error_count = 0

    if not pdf_files:
        logger.info(f"No PDF files found in {directory}")
        return 0, 0, 0

    logger.info(f"Found {len(pdf_files)} PDF files. Counting pages...")

    for pdf_path in tqdm(pdf_files, desc="Counting PDF pages"):
        try:
            reader = PdfReader(pdf_path)
            total_pages += len(reader.pages)
        except PdfReadError as e:
            logger.warning(f"Could not read '{pdf_path.name}': {e}")
            error_count += 1
        except Exception as e:
            logger.error(f"An unexpected error occurred with '{pdf_path.name}': {e}")
            error_count += 1

    file_count = len(pdf_files) - error_count
    return total_pages, file_count, error_count


def main():
   
    parser = argparse.ArgumentParser(description="Count total pages of PDF files in a directory.")
    parser.add_argument(
        "--pdf-dir", type=str, default="data/pdfs", help="The directory containing PDF files."
    )
    args = parser.parse_args()

    pdf_directory = Path(args.pdf_dir)
    total_pages, success_count, error_count = count_pages_in_directory(pdf_directory)

    print("\n--- Page Count Summary ---")
    print(f"Total pages in {success_count} PDF(s): {total_pages}")
    if error_count > 0:
        print(f"Could not process {error_count} file(s). Check logs for details.")


if __name__ == "__main__":
    main()