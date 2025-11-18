#!/usr/bin/env python3
"""Extract text from books to plain text files."""

import sys
import argparse
from pathlib import Path
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config_loader import get_config
from logger import setup_logger
from text_extractor import TextExtractor


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Extract text from book files"
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--input',
        '-i',
        type=str,
        help='Input file or directory'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        help='Output directory for text files'
    )
    parser.add_argument(
        '--format',
        '-f',
        type=str,
        help='Filter by file format (e.g., .pdf, .epub)'
    )

    args = parser.parse_args()

    # Load configuration
    config = get_config(args.config)

    # Setup logger
    logger = setup_logger(
        name="extract_text",
        log_file=str(config.logs_path / "extract_text.log"),
        level=config.get('logging.level', 'INFO')
    )

    # Get input path
    if args.input:
        input_path = Path(args.input)
    else:
        input_path = config.books_path

    # Get output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = config.text_output_path

    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Input path: {input_path}")
    logger.info(f"Output path: {output_path}")

    # Get files to process
    if input_path.is_file():
        files = [input_path]
    else:
        supported_formats = config.get_supported_formats()
        if args.format:
            supported_formats = [args.format if args.format.startswith('.') else f'.{args.format}']

        files = []
        for format_ext in supported_formats:
            files.extend(input_path.glob(f"**/*{format_ext}"))

    if not files:
        logger.warning(f"No files found in {input_path}")
        return 0

    logger.info(f"Found {len(files)} files to process")

    # Initialize extractor
    extractor = TextExtractor(logger=logger)

    # Process files
    successful = 0
    failed = 0

    for file_path in tqdm(files, desc="Extracting text"):
        try:
            # Extract text
            text, metadata = extractor.extract(file_path)

            if not text:
                logger.warning(f"No text extracted from {file_path.name}")
                failed += 1
                continue

            # Save to file
            output_file = output_path / f"{file_path.stem}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                # Write metadata as header
                f.write(f"Source: {file_path.name}\n")
                if metadata.get('title'):
                    f.write(f"Title: {metadata['title']}\n")
                if metadata.get('author'):
                    f.write(f"Author: {metadata['author']}\n")
                if metadata.get('word_count'):
                    f.write(f"Words: {metadata['word_count']}\n")
                f.write("\n" + "=" * 80 + "\n\n")

                # Write text
                f.write(text)

            logger.info(f"Saved {output_file.name} ({metadata.get('word_count', 0)} words)")
            successful += 1

        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {str(e)}")
            failed += 1

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Extraction complete!")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Output directory: {output_path}")
    logger.info("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
