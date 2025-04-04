import os
import json
from typing import Dict, Any, Optional
from .config import settings
from .logger import storage_logger as logger

class StorageService:
    """Centralized service for handling all file operations"""
    
    def __init__(self):
        self.raw_dir = settings.RAW_DATA_DIR
        self.processed_dir = settings.PROCESSED_DATA_DIR
        self.json_inputs_dir = settings.JSON_INPUTS_DIR
        
        # Ensure directories exist
        for directory in [self.raw_dir, self.processed_dir, self.json_inputs_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def save_raw_data(self, data: Dict[str, Any], prefix: str, identifier: str) -> str:
        """Save raw data (e.g., SERP results, raw tweets)"""
        clean_id = self._clean_filename(identifier)
        filename = f"{prefix}_{clean_id}.json"
        filepath = os.path.join(self.raw_dir, filename)
        
        return self._save_json(data, filepath)
    
    def save_processed_data(self, data: Dict[str, Any], prefix: str, identifier: str) -> str:
        """Save intermediate processed data"""
        clean_id = self._clean_filename(identifier)
        filename = f"{prefix}_{clean_id}.json"
        filepath = os.path.join(self.processed_dir, filename)
        
        return self._save_json(data, filepath)
    
    def save_final_data(self, data: Dict[str, Any], prefix: str, identifier: str) -> str:
        """Save final data that matches database models"""
        clean_id = self._clean_filename(identifier)
        filename = f"{prefix}_{clean_id}.json"
        filepath = os.path.join(self.json_inputs_dir, filename)
        
        return self._save_json(data, filepath)
    
    def load_data(self, prefix: str, identifier: str, directory: str) -> Optional[Dict[str, Any]]:
        """Load data file for a given prefix and identifier"""
        clean_id = self._clean_filename(identifier)
        filename = f"{prefix}_{clean_id}.json"
        filepath = os.path.join(directory, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading file {filepath}: {str(e)}")
            return None
    
    def get_file_path(self, prefix: str, identifier: str, directory: str) -> Optional[str]:
        """Get the path of the data file for a given prefix and identifier"""
        clean_id = self._clean_filename(identifier)
        filename = f"{prefix}_{clean_id}.json"
        filepath = os.path.join(directory, filename)
        
        return filepath if os.path.exists(filepath) else None
    
    def _clean_filename(self, name: str) -> str:
        """Clean a string to be used in a filename"""
        return ''.join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
    
    def _save_json(self, data: Dict[str, Any], filepath: str) -> str:
        """Save JSON data to file"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved data to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving to {filepath}: {str(e)}")
            raise 