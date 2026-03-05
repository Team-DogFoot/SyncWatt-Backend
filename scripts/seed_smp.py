import argparse
import logging
import os
import sys

# Ensure the app directory is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import init_db
from app.services.external.smp_service import smp_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("seed_smp")

def main():
    parser = argparse.ArgumentParser(description="Seed SMP data from Excel files to the database.")
    parser.add_argument(
        "--files", 
        nargs="+", 
        help="List of Excel file paths to load. If omitted, uses default paths.",
        default=[
            "/Users/kkh/Downloads/smp_land_2026.xlsx",
            "/Users/kkh/Downloads/smp_land_2025.xlsx"
        ]
    )
    
    args = parser.parse_args()
    
    logger.info("Initializing database tables...")
    init_db()
    
    logger.info(f"Loading SMP data from {len(args.files)} files...")
    
    # Optional: If smp_service.load_smp_data were modified to accept paths,
    # we would pass args.files here. Currently it uses its internal defaults.
    # For now, let's make it more flexible.
    
    # Overriding internal paths temporarily if user provided custom ones
    original_paths = smp_service.file_paths
    smp_service.file_paths = args.files
    
    try:
        smp_service.load_smp_data()
        logger.info("SMP data seeding complete.")
    except Exception as e:
        logger.error(f"Seeding failed: {str(e)}")
        sys.exit(1)
    finally:
        smp_service.file_paths = original_paths

if __name__ == "__main__":
    main()
