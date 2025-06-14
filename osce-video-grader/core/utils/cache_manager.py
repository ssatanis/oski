import os
import json
import fcntl # For file locking on POSIX systems (Linux/macOS)
from typing import Dict, Any, Optional

DEFAULT_CACHE_FILE_PATH = "./pipeline_cache.json"

class JsonCache:
    def __init__(self, cache_file_path: str = DEFAULT_CACHE_FILE_PATH):
        self.cache_file_path = cache_file_path
        self.cache_data: Dict[str, Any] = self._load_cache_file()

    def _acquire_lock(self, file_handle, lock_type):
        try:
            fcntl.flock(file_handle.fileno(), lock_type)
            return True
        except (IOError, AttributeError, ImportError): # Handles unavailable fcntl or errors
            # print(f"Warning: fcntl not available or failed for file locking (likely Windows or specific OS issue). Proceeding without lock.")
            return False

    def _release_lock(self, file_handle):
        try:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
        except (IOError, AttributeError, ImportError):
            pass # Silently pass if unlock fails (e.g., lock was not acquired)

    def _load_cache_file(self) -> Dict[str, Any]:
        if not os.path.exists(self.cache_file_path):
            return {}
        try:
            with open(self.cache_file_path, 'r') as f:
                locked = self._acquire_lock(f, fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    print(f"Warning: Cache file '{self.cache_file_path}' is corrupted. Initializing with empty cache.")
                    data = {}
                finally:
                    if locked: self._release_lock(f)
            return data
        except IOError as e:
            print(f"Warning: Could not read cache file '{self.cache_file_path}': {e}. Initializing with empty cache.")
            return {}
        except Exception as e:
            print(f"Warning: An unexpected error occurred loading cache '{self.cache_file_path}': {e}. Initializing with empty cache.")
            return {} # Gracefully handle other errors

    def _save_cache_file(self):
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.cache_file_path) or '.', exist_ok=True)
            with open(self.cache_file_path, 'w') as f:
                locked = self._acquire_lock(f, fcntl.LOCK_EX)
                try:
                    json.dump(self.cache_data, f, indent=4)
                finally:
                    if locked: self._release_lock(f)
            # print(f"Cache saved to '{self.cache_file_path}'.")
        except IOError as e:
            print(f"Error: Could not write to cache file '{self.cache_file_path}': {e}")
        except Exception as e:
            print(f"Warning: An unexpected error occurred saving cache '{self.cache_file_path}': {e}.")


    def get_item(self, category: str, key: str) -> Optional[Any]:
        """Gets an item from a specific category in the cache."""
        return self.cache_data.get(category, {}).get(key)

    def set_item(self, category: str, key: str, value: Any):
        """Sets an item in a specific category in the cache and saves the cache."""
        if category not in self.cache_data:
            self.cache_data[category] = {}
        self.cache_data[category][key] = value
        self._save_cache_file()

    def clear_category(self, category: str):
        """Clears all items from a specific category."""
        if category in self.cache_data:
            del self.cache_data[category]
            self._save_cache_file()

    def clear_all(self):
        """Clears the entire cache."""
        self.cache_data = {}
        self._save_cache_file()