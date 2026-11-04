"""
Summary:

The Data class is a utility for managing structured data, including groups, categories, tags, and thumbnail metadata.
It interacts with a JSON-based data storage system (via DataJson) and application preferences (via Preferences) to
provide a clean and efficient interface for data manipulation.

Key Features:

    Group Management:
        Add, remove, and retrieve groups.
        Organize data into hierarchical structures.

    Category Management:
        Add, rename, and remove categories within groups.
        Retrieve categories for a specific group.

    Thumbnail Data Management:
        Add thumbnail metadata (e.g., source file, proxy file, resolution) to categories.
        Retrieve and filter thumbnail data by tags or search strings.

    Tag Management:
        Create, add, and remove tags.
        Associate tags with specific thumbnail data entries.

    Data Refresh:
        Reload data from the JSON file to reflect changes made externally.
"""

# -------------------------------- built-in Modules ----------------------------------
import os
from typing import Generator, Dict, List

# ------------------------------- ThirdParty Modules ---------------------------------

# -------------------------------- Custom Modules ------------------------------------
from . import _handler
from . import _media


class Data:
    """
    A class for managing data operations, including groups, categories, tags, and thumbnails.

    This class provides methods to interact with the JSON data structure managed by `DataJson`
    and application preferences managed by `Preferences`.

    Attributes:
        preferences (_handler.Preferences): Instance of the Preferences class.
        data_obj (_handler.DataJson): Instance of the DataJson class.
        __data (Dict): Internal data structure for storing JSON data.
        __tags (List[str]): List of tags from the JSON data.
    """

    def __init__(self):
        """
        Initialize the Data class.
        Loads preferences and initializes the data object.
        """
        self.preferences = _handler.Preferences()
        self.data_obj = _handler.DataJson(self.preferences.data_file, self.preferences.footage_root)
        self.__data = self.data_obj.data
        self.__tags = self.data_obj.tags

    def groups(self) -> Generator[str, None, None]:
        """
        Get group names from the JSON data.

        :return: Generator yielding group names.
        :rtype: Generator[str, None, None]
        """
        if self.__data:
            for group, _ in self.__data.items():
                yield group

    def add_group(self, group: str) -> None:
        """
        Add a group to the JSON data.

        :param group: Name of the group to add.
        :type group: str
        """
        self.data_obj.update_data(group=group)

    def remove_group(self, group: str) -> None:
        """
        Remove a group from the JSON data.

        :param group: Name of the group to remove.
        :type group: str
        """
        self.data_obj.remove_key(group=group)

    def add_category(self, group: str, category: str) -> None:
        """
        Add a category to a group in the JSON data.

        :param group: Name of the group.
        :type group: str
        :param category: Name of the category to add.
        :type category: str
        """
        self.data_obj.update_data(group=group, category=category)

    def rename_category(self, group: str, old_category: str, new_category: str) -> None:
        """
        Rename a category in a group.

        :param group: Name of the group.
        :type group: str
        :param old_category: Current name of the category.
        :type old_category: str
        :param new_category: New name for the category.
        :type new_category: str
        """
        self.data_obj.update_key(group, old_category, new_category)

    def remove_category(self, group: str, category: str) -> None:
        """
        Remove a category from a group.

        :param group: Name of the group.
        :type group: str
        :param category: Name of the category to remove.
        :type category: str
        """
        self.data_obj.remove_key(group=group, category=category)

    def categories(self, group: str) -> Generator[str, None, None]:
        """
        Get categories of a given group.

        :param group: Name of the group.
        :type group: str
        :return: Generator yielding category names.
        :rtype: Generator[str, None, None]
        """
        if self.__data.get(group):
            for category in self.__data[group].keys():
                yield category

    def add_proxy_data(self, data: dict, group: str, category: str) -> None:
        """
        Add proxy data to a category in a group.

        :param data: proxy data to update
        :type data: dict
        :param group: Name of the group.
        :type group: str
        :param category: Name of the category.
        :type category: str
        """
        self.data_obj.update_data(group=group, category=category, data=data)

    def thumbnail_data(self, group: str, category: str, tag: str = None, search_string: str = None) -> List[Dict]:
        """
        Get thumbnail data for a category, optionally filtered by tag or search string.

        :param group: Name of the group.
        :type group: str
        :param category: Name of the category.
        :type category: str
        :param tag: Tag to filter by.
        :type tag: Optional[str]
        :param search_string: String to search in source file names.
        :type search_string: Optional[str]
        :return: List of thumbnail data matching the criteria.
        :rtype: List[Dict]
        """
        category_data = self.data_obj.data[group].get(category, [])

        if not tag and not search_string:
            return category_data

        elif tag and not search_string:
            return [data for data in category_data if tag in data['tags']]

        elif not tag and search_string:
            return [data for data in category_data if search_string.lower() in os.path.basename(data['source']).lower()]
        else:
            return [data for data in category_data
                    if search_string.lower() in os.path.basename(data['source']).lower() and tag in data['tags']]

    def remove_data(self, group: str, category: str, source_files: List[str]) -> None:
        """
        Remove data from a category.

        :param group: Name of the group.
        :type group: str
        :param category: Name of the category.
        :type category: str
        :param source_files: List of source files to remove.
        :type source_files: List[str]
        """
        self.data_obj.remove_data(group=group, category=category, source_files=source_files)

    @property
    def tags(self) -> List[str]:
        """
        Get the list of tags.

        :return: List of tags.
        :rtype: List[str]
        """
        return self.__tags

    def create_tag(self, tag: str) -> None:
        """
        Create a new tag.

        :param tag: Name of the tag to create.
        :type tag: str
        """
        self.data_obj.update_data(data_type='tags', tag=tag)
        self.__tags.append(tag)

    def add_tag(self, group: str, category: str, source_files: List[str], tag: str) -> None:
        """
        Add a tag to specific data entries.

        :param group: Name of the group.
        :type group: str
        :param category: Name of the category.
        :type category: str
        :param source_files: List of source files to tag.
        :type source_files: List[str]
        :param tag: Tag to add.
        :type tag: str
        """
        self.data_obj.update_data(group=group, category=category, source_files=source_files, tag=tag)

    def remove_tag(self, group: str, category: str, source_files: List[str], tag: str) -> None:
        """
        Remove a tag from specific data entries.

        :param group: Name of the group.
        :type group: str
        :param category: Name of the category.
        :type category: str
        :param source_files: List of source files to untag.
        :type source_files: List[str]
        :param tag: Tag to remove.
        :type tag: str
        """
        self.data_obj.remove_data(group=group, category=category, source_files=source_files, tag=tag)

    def is_category_exists(self, group: str, category: str) -> bool:
        """
        Check if a category exists in a group.

        :param group: Name of the group.
        :type group: str
        :param category: Name of the category.
        :type category: str
        :return: True if the category exists, False otherwise.
        :rtype: bool
        """
        return self.data_obj.is_category_item_exists(group, category)

    def plan_reconnect(self, search_root: str, cancelled=None, progress=None) -> dict:
        """
        Scan a folder for missing source and proxy files. Nothing is written.

        :param search_root: Folder to search for the moved footage.
        :param cancelled: Optional callable, returns True to stop the scan.
        :param progress: Optional callable receiving status text.
        :return: Plan dict with keys: changes, stats, search_root.
        """
        raw = self.data_obj.deserialize()
        source_index = _media.build_index(search_root, cancelled, progress)
        proxy_index = _media.build_index(self.preferences.proxy, cancelled, progress)
        changes, stats = _media.plan_reconnect(raw, source_index, proxy_index, cancelled=cancelled)
        return {'changes': changes, 'stats': stats, 'search_root': search_root}

    def apply_reconnect(self, plan: dict) -> dict:
        """
        Back up data.json, write the planned changes and make the search root the footage root.

        :param plan: Plan from plan_reconnect (its 'changes' may be a filtered subset).
        :return: Dict with keys: applied, backup.
        """
        backup = _media.backup_file(self.data_obj.json_file)

        # Read and apply with the OLD root, so the paths match the plan.
        raw = self.data_obj.deserialize()
        applied = _media.apply_changes(raw, plan['changes'])

        # Switch the root only when writing, so new paths are stored as tokens.
        if plan['search_root'] != self.preferences.footage_root:
            self.preferences.update({'footage_root': plan['search_root']})
            self.data_obj.footage_root = plan['search_root']

        self.data_obj.serialize(raw)
        self.refresh()

        return {'applied': applied, 'backup': backup}

    def relink_source(self, group: str, category: str, old_source: str, new_source: str) -> bool:
        """
        Point one item's source to a new file, back up data.json, then save.

        :return: True if the item was found and updated.
        """
        raw = self.data_obj.deserialize()
        for item in raw['data'].get(group, {}).get(category, []):
            if item.get('source') == old_source:
                _media.backup_file(self.data_obj.json_file)
                item['source'] = _media._normalize(new_source)
                _media.set_name_metadata(item.setdefault('metadata', {}), item['source'])
                self.data_obj.serialize(raw)
                self.refresh()
                return True
        return False

    def refresh(self) -> None:
        """
        Refresh the data from the JSON file.

        Updates the internal data and tags after reloading from the JSON file.
        """
        self.data_obj.json_file = self.preferences.data_file
        self.data_obj.footage_root = self.preferences.footage_root
        self.data_obj.refresh_data()
        self.__data = self.data_obj.data
