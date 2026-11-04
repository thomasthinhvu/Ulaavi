"""
Helpers for the source file name metadata and for reconnecting missing media.

- set_name_metadata: stores the source file name under metadata['name'],
  placed right after the 'Tags' entry.
- build_index: maps lower-cased file names to their full paths under a folder.
- reconnect_items: rewrites 'source' and 'proxy' paths that no longer exist,
  using the index. Works on the dict loaded from data.json.
"""
import os
from typing import Dict, List

NAME_KEY = 'name'
TAGS_KEY = 'Tags'


def _normalize(path: str) -> str:
    """Return the path with forward slashes."""
    return path.replace('\\', '/')


def set_name_metadata(metadata: dict, source: str) -> dict:
    """
    Set metadata['name'] to the file name of the source, placed right after 'Tags'.

    The dict is modified in place and also returned.

    :param metadata: Metadata dict of one data.json item.
    :param source: Full path of the source file.
    """
    name = os.path.basename(_normalize(source)) if source else ''

    items = [(key, value) for key, value in metadata.items() if key != NAME_KEY]
    metadata.clear()
    for key, value in items:
        metadata[key] = value
        if key == TAGS_KEY:
            metadata[NAME_KEY] = name

    if NAME_KEY not in metadata:
        metadata[NAME_KEY] = name

    return metadata


def build_index(root: str) -> Dict[str, List[str]]:
    """
    Walk a folder once and map each lower-cased file name to its full paths.

    :param root: Folder to search. Missing or empty values give an empty index.
    :return: Dict of file name -> list of full paths.
    """
    index: Dict[str, List[str]] = {}
    if not root or not os.path.isdir(root):
        return index

    for dir_path, _, file_names in os.walk(root):
        for file_name in file_names:
            full_path = _normalize(os.path.join(dir_path, file_name))
            index.setdefault(file_name.lower(), []).append(full_path)

    return index


def _tail_score(candidate: str, old_path: str) -> int:
    """Count how many trailing folder/file parts two paths share (case-insensitive)."""
    new_parts = _normalize(candidate).split('/')[::-1]
    old_parts = _normalize(old_path).split('/')[::-1]

    score = 0
    for new_part, old_part in zip(new_parts, old_parts):
        if new_part.lower() != old_part.lower():
            break
        score += 1
    return score


def _pick_candidate(candidates: List[str], old_path: str) -> str:
    """Pick the candidate that shares the most trailing path parts with the old path."""
    return max(candidates, key=lambda candidate: _tail_score(candidate, old_path))


def reconnect_items(data: dict, source_index: Dict[str, List[str]], proxy_index: Dict[str, List[str]] = None) -> dict:
    """
    Relink missing source and proxy paths in a loaded data.json dict.

    Every item also gets its metadata['name'] set/updated.
    The dict is modified in place.

    :param data: Full data.json content ({'data': {...}, 'tags': [...]}).
    :param source_index: Index of the search folder for source files (see build_index).
    :param proxy_index: Optional index of the proxy folder for proxy files.
    :return: Stats dict with keys: checked, ok, relinked, proxy_relinked, missing.
    """
    stats = {'checked': 0, 'ok': 0, 'relinked': 0, 'proxy_relinked': 0, 'missing': []}

    for categories in data.get('data', {}).values():
        for items in categories.values():
            for item in items:
                stats['checked'] += 1

                source = item.get('source', '')
                set_name_metadata(item.setdefault('metadata', {}), source)

                if source and os.path.exists(source):
                    stats['ok'] += 1
                elif source:
                    candidates = source_index.get(os.path.basename(_normalize(source)).lower(), [])
                    if candidates:
                        item['source'] = _pick_candidate(candidates, source)
                        stats['relinked'] += 1
                    else:
                        stats['missing'].append(source)

                proxy = item.get('proxy', '')
                if proxy and not os.path.exists(proxy) and proxy_index:
                    candidates = proxy_index.get(os.path.basename(_normalize(proxy)).lower(), [])
                    if candidates:
                        item['proxy'] = _pick_candidate(candidates, proxy)
                        stats['proxy_relinked'] += 1

    return stats
