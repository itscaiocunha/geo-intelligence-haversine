import logging
import os

os.makedirs("data", exist_ok=True)

file_handler = logging.FileHandler("data/operation.log", mode='a', encoding='utf-8')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [GEO-INT] - %(message)s',
    handlers=[
        file_handler,
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("geo_intelligence")