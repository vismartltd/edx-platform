"""
Provides factories for Bookmark models.
"""

from factory.django import DjangoModelFactory
from factory import SubFactory
from functools import partial

from student.tests.factories import UserFactory
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from ..models import Bookmark

# pylint: disable=invalid-name
course_id = SlashSeparatedCourseKey(u'edX', u'test_course', u'test')
location = partial(course_id.make_usage_key, u'problem')


class BookmarkFactory(DjangoModelFactory):
    """ Simple factory class for generating Bookmark """
    FACTORY_FOR = Bookmark

    user = SubFactory(UserFactory)
    course_key = course_id
    usage_key = location('usage_id')
    display_name = ""
    path = dict()
