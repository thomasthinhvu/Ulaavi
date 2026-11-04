"""
Helpers for source file names, missing media and the footage root token.

- set_name_metadata: stores the source file name under metadata['name'], right after 'Tags'.
- build_index: maps lower-cased file names to full paths under a folder (cancellable).
- plan_reconnect: finds replacements for missing source/proxy paths without changing data.
- apply_changes: writes the chosen replacements back into the data dict.
- expand_footage_root / collapse_footage_root: store footage paths as '${FOOTAGE_ROOT}/...'
  in data.json, so moving the whole library only needs the root to change.
- backup_file: copies data.json before it is rewritten.
"""
import copy
import datetime
import os
import shutil
from typing import Callable, Dict, List, Optional, Tuple

NAME_KEY = 'name'
TAGS_KEY = 'Tags'
FOOTAGE_TOKEN = '${FOOTAGE_ROOT}'


class ReconnectCancelled(Exception):
    """Raised when the user cancels a scan."""


def _normalize(path: str) -> str:
    """Return the path with forward slashes."""
    return path.replace('\\', '/')


# ----------------------------------------------------------------------------
# Name metadata
# ----------------------------------------------------------------------------
def set_name_metadata(metadata: dict, source: str) -> dict:
    """
    Set metadata['name'] to the source file name, placed right after 'Tags'.

    The dict is modified in place and also returned.
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


# ----------------------------------------------------------------------------
# Indexing and matching
# ----------------------------------------------------------------------------
def build_index(root: str,
                cancelled: Optional[Callable[[], bool]] = None,
                progress: Optional[Callable[[str], None]] = None) -> Dict[str, List[str]]:
    """
    Walk a folder and map each lower-cased file name to its full paths.

    :raises ReconnectCancelled: if `cancelled()` returns True during the walk.
    """
    index: Dict[str, List[str]] = {}
    if not root or not os.path.isdir(root):
        return index

    for dir_path, _, file_names in os.walk(root):
        if cancelled and cancelled():
            raise ReconnectCancelled()
        if progress:
            progress(f'Scanning {dir_path}')

        for file_name in file_names:
            full_path = _normalize(os.path.join(dir_path, file_name))
            index.setdefault(file_name.lower(), []).append(full_path)

    return index


def probe_video(path: str) -> Optional[Dict[str, int]]:
    """
    Read width, height and frame count of a video with OpenCV.

    Returns None if OpenCV is unavailable or the file cannot be opened.
    """
    try:
        import cv2
    except ImportError:
        return None

    capture = cv2.VideoCapture(path)
    try:
        if not capture.isOpened():
            return None
        return {'width': int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'frames': int(capture.get(cv2.CAP_PROP_FRAME_COUNT))}
    finally:
        capture.release()


def _matches_metadata(metadata: dict, info: Dict[str, int]) -> bool:
    """Compare stored metadata (width, height, Frame(s)) with a probed file."""
    if metadata.get('width') and int(metadata['width']) != info['width']:
        return False
    if metadata.get('height') and int(metadata['height']) != info['height']:
        return False
    try:
        stored_frames = int(metadata.get('Frame(s)', 0))
    except (TypeError, ValueError):
        return True
    return not (stored_frames and info['frames'] and stored_frames != info['frames'])


def _tail_score(candidate: str, old_path: str) -> int:
    """Count how many trailing path parts two paths share (case-insensitive)."""
    new_parts = _normalize(candidate).split('/')[::-1]
    old_parts = _normalize(old_path).split('/')[::-1]

    score = 0
    for new_part, old_part in zip(new_parts, old_parts):
        if new_part.lower() != old_part.lower():
            break
        score += 1
    return score


def pick_candidate(candidates: List[str],
                   old_path: str,
                   metadata: dict,
                   probe_fn: Callable[[str], Optional[Dict[str, int]]] = probe_video) -> Optional[str]:
    """
    Choose the replacement file for a missing path.

    - One candidate with that name: use it.
    - Several candidates: keep only those whose width, height and frame count match the
      stored metadata, then take the one closest to the old path.
    - Several candidates and none match: return None rather than guess.
    """
    if len(candidates) == 1:
        return candidates[0]

    matches = []
    for candidate in candidates:
        info = probe_fn(candidate)
        if info and _matches_metadata(metadata, info):
            matches.append(candidate)

    if not matches:
        return None
    return max(matches, key=lambda candidate: _tail_score(candidate, old_path))


# ----------------------------------------------------------------------------
# Plan and apply
# ----------------------------------------------------------------------------
def plan_reconnect(data: dict,
                   source_index: Dict[str, List[str]],
                   proxy_index: Optional[Dict[str, List[str]]] = None,
                   probe_fn: Callable[[str], Optional[Dict[str, int]]] = probe_video,
                   cancelled: Optional[Callable[[], bool]] = None) -> Tuple[List[dict], dict]:
    """
    Work out which source and proxy paths need relinking. The data dict is NOT changed.

    :return: (changes, stats). Each change is a dict with keys:
             group, category, index, field ('source' or 'proxy'), old, new.
    """
    changes: List[dict] = []
    stats = {'checked': 0, 'ok': 0, 'relinked': 0, 'proxy_relinked': 0,
             'missing': [], 'ambiguous': []}

    for group, categories in data.get('data', {}).items():
        for category, items in categories.items():
            for index, item in enumerate(items):
                if cancelled and cancelled():
                    raise ReconnectCancelled()

                stats['checked'] += 1
                metadata = item.get('metadata', {})
                source = item.get('source', '')

                if source and os.path.exists(source):
                    stats['ok'] += 1
                elif source:
                    candidates = source_index.get(os.path.basename(_normalize(source)).lower(), [])
                    new_path = pick_candidate(candidates, source, metadata, probe_fn) if candidates else None
                    if new_path:
                        changes.append({'group': group, 'category': category, 'index': index,
                                        'field': 'source', 'old': source, 'new': _normalize(new_path)})
                        stats['relinked'] += 1
                    elif candidates:
                        stats['ambiguous'].append(source)
                    else:
                        stats['missing'].append(source)

                proxy = item.get('proxy', '')
                if proxy and not os.path.exists(proxy) and proxy_index:
                    candidates = proxy_index.get(os.path.basename(_normalize(proxy)).lower(), [])
                    if len(candidates) >= 1:
                        changes.append({'group': group, 'category': category, 'index': index,
                                        'field': 'proxy', 'old': proxy,
                                        'new': _normalize(candidates[0])})
                        stats['proxy_relinked'] += 1

    return changes, stats


def apply_changes(data: dict, changes: List[dict]) -> int:
    """
    Write planned changes into the data dict. A change is skipped if the stored path
    no longer equals the old path it was planned from.

    Every item also gets its metadata['name'] refreshed.

    :return: number of changes applied.
    """
    applied = 0
    for change in changes:
        try:
            item = data['data'][change['group']][change['category']][change['index']]
        except (KeyError, IndexError):
            continue
        if item.get(change['field']) != change['old']:
            continue
        item[change['field']] = change['new']
        applied += 1

    for categories in data.get('data', {}).values():
        for items in categories.values():
            for item in items:
                set_name_metadata(item.setdefault('metadata', {}), item.get('source', ''))

    return applied


# ----------------------------------------------------------------------------
# Footage root token
# ----------------------------------------------------------------------------
def _iter_source_items(data: dict):
    for categories in data.get('data', {}).values():
        for items in categories.values():
            for item in items:
                yield item


def expand_footage_root(data: dict, root: str) -> dict:
    """Replace '${FOOTAGE_ROOT}' in source paths with the real root. Modifies data in place."""
    if not root:
        return data
    root = _normalize(root).rstrip('/')
    for item in _iter_source_items(data):
        source = item.get('source', '')
        if source.startswith(FOOTAGE_TOKEN):
            item['source'] = root + source[len(FOOTAGE_TOKEN):]
    return data


def collapse_footage_root(data: dict, root: str) -> dict:
    """
    Return a copy of data where source paths under `root` are stored as '${FOOTAGE_ROOT}/...'.
    The input is not changed.
    """
    result = copy.deepcopy(data)
    if not root:
        return result
    root = _normalize(root).rstrip('/')
    prefix = root.lower() + '/'
    for item in _iter_source_items(result):
        source = _normalize(item.get('source', ''))
        if source.lower().startswith(prefix):
            item['source'] = FOOTAGE_TOKEN + source[len(root):]
    return result


# ----------------------------------------------------------------------------
# Backup
# ----------------------------------------------------------------------------
def backup_file(path: str) -> Optional[str]:
    """
    Copy `path` to '<path>.bak-YYYYMMDD-HHMMSS' in the same folder.

    :return: the backup path, or None if the file does not exist yet.
    """
    if not path or not os.path.isfile(path):
        return None
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_path = f'{path}.bak-{stamp}'
    shutil.copy2(path, backup_path)
    return backup_path
