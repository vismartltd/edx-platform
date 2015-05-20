"""
This File contains Model for Bookmarks.
"""

import json
import logging

from django.contrib.auth.models import User
from django.db import models
from model_utils.models import TimeStampedModel

from xmodule.modulestore.django import modulestore
from xmodule_django.models import CourseKeyField, LocationKeyField

log = logging.getLogger(__name__)


class Bookmark(models.Model):
    """
    Bookmarks model.
    """
    user = models.ForeignKey(User)
    course_key = CourseKeyField(max_length=255, db_index=True)
    usage_key = LocationKeyField(max_length=255, db_index=True)
    _path = models.TextField(db_column='path', null=True, blank=True, help_text="JSON, breadcrumbs to the XBlock")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    block_cache = models.ForeignKey(XBlockCache, null=True, blank=True)

    @property
    def display_name(self):
        return self.block_cache.display_name

    @property
    def path(self):
        """
        Parse the path json from the _path field and return it.
        """
        if self.updated < self.block_cache.updated:
            block = modulestore().get_item(self.usage_key)
            self.path = Bookmark.get_path(block)

        return json.loads(self._path)

    @path.setter
    def path(self, value):
        """
        Sets the Parsed path to json.
        """
        self._path = json.dumps(value)

    @classmethod
    def create(cls, bookmarks_data, block=None):
        """
        Create the bookmark object.
        """
        if not block:
            block = modulestore().get_item(bookmarks_data['usage_key'])

        bookmarks_data['display_name'] = block.display_name
        bookmarks_data['_path'] = json.dumps(cls.get_path(block))
        bookmarks_data['block_cache'], __ = XBlockCache.objects.get_or_create(
            course_key=bookmark_data['course_key'], usage_key=bookmark_data['usage_key'],
        )

        bookmark, __ = cls.objects.get_or_create(**bookmarks_data)
        return bookmark

    @staticmethod
    def get_path(block):
        """
        Returns List of dicts containing {"usage_id": "", display_name:""} for the XBlocks
        from the top of the course tree till the parent of the bookmarked XBlock.
        """

        # This method may not return the "correct" result if one block has multiple parents, and the
        # student does not have access to one of those parents.
        parent = block.get_parent()
        parents_data = []

        while parent is not None and parent.location.block_type not in ['course']:
            parents_data.append({"display_name": parent.display_name, "usage_id": unicode(parent.location)})
            parent = parent.get_parent()
        parents_data = parents_data[:2]  # To exclude the unit/vertical block information.
        parents_data.reverse()
        return parents_data


class XBlockCache(TimeStampedModel):

    course_key = CourseKeyField(max_length=255, db_index=True)
    usage_key = LocationKeyField(max_length=255, db_index=True, unique=True)

    display_name = models.CharField(max_length=255, default="")
    _paths = models.TextField(db_column='paths', null=True, blank=True)

    @property
    def paths(self):
        """
        Parse JSON from the _paths field and return it.
        """
        return json.loads(self._paths)

    @path.setter
    def paths(self, value):
        """
        Set data as JSON on the _paths field.
        """
        self._path = json.dumps(value)
