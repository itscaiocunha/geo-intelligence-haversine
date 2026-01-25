import logging
import os
import sys

# Define the absolute path to avoid ambiguities in Docker.
LOG_DIR = "data"
LOG_FILE = os.path.join(LOG_DIR, "operation.log")

# Ensures the existence of the directory with broad permissions.
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

# Detailed formatter configuration
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [GEO-INT] - %(message)s')

# Handler for file (Persistence)
file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
file_handler.setFormatter(log_formatter)

# Handler for console (Direct visualization in Docker Logs)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

# Configuration of the Root Logger
logger = logging.getLogger("geo_intelligence")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Boot log to test if the file is created at boot.
logger.info("Audit system initialized and logging started.")