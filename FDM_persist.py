import os
import json


def _areas_file_path(self):
    try:
        base = os.path.dirname(__file__)
    except Exception:
        base = os.getcwd()
    return os.path.join(base, 'saved_areas.json')


def _persist_saved_areas(self):
    try:
        path = self._areas_file_path()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self._saved_areas, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _load_saved_areas(self):
    try:
        path = self._areas_file_path()
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                cleaned = []
                for it in data:
                    if isinstance(it, (list, tuple)) and len(it) == 4:
                        cleaned.append(tuple(it))
                self._saved_areas = cleaned
    except Exception:
        pass

