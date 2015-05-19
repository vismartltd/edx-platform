"""
Django models related to teams functionality.
"""

from django.contrib.auth.models import User
from django.db import models
from .utils import slugify

from ..course_groups.models import CourseUserGroup

class CourseTeam(models.Model):
    """
    This model represents team related info.
    """
    course_user_group = models.OneToOneField(CourseUserGroup, unique=True, related_name='team')

    """
    id	The unique id of a team. Note that the id will be used in URLs so should be a human readable string rather than an integer. In addition, the id is globally unique, not just per course.	(error)
    name	The name of the team	(tick)	is_staff
    is_active	Returns true if the team is currently active. If set to false, the team is considered to be "soft deleted" and will not be returned by default when listing topics.	(tick)	is_staff
    course_id	The id of the course that this team belongs to. Note that eventually this field could be optional if global teams are supported.	(error)
    topic_id	An optional field that declares which topic this team is associated with	(tick)	is_staff
    date_created	The timestamp for when this team was created	(error)
    last_activity	The timestamp when an activity last happened for this team (usually, a discussion post).	(error)
    description	A description of the team. Note: HTML text will not be supported in the description.	(tick)	is_staff
    country	An optional field specifying a country affiliation for the team	(tick)	is_staff
    language

    An optional field specifying the language that will be used by this team
    (tick)	is_staff
    membership	Returns membership information for the team. Note that this is a read-only field, and that the team membership end points should be used for updates.	(error)
    """

    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    topic_id = models.CharField(max_length=100, db_index=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    # last_activity is computed through a query
    description = models.CharField(max_length=1000)
    country = models.CharField(max_length=50, blank=True)
    language = models.CharField(max_length=20, blank=True)
    # membership is computed through a query

    @classmethod
    def create(cls, team_name, course_id, description, topic_id=None, course_user_group=None, country=None, language=None):
        """
        Create a complete (CourseUserGroup + CourseTeam) object.

        Args:
            team_name: Name of the team to be created
            course_id: Course id
            description: Description of the team
            topic_id: Identifier for the topic the team formed around
            course_user_group: CourseUserGroup
            country: Country where the team is based
            language: Language the team uses
        """

        team_id = slugify(team_name)
        conflicts = CourseUserGroup.objects.filter(name__startswith=team_id).values_list('name', flat=True)

        if conflicts and team_id in conflicts:
            suffix = 2
            while True:
                new_id = team_id + '-' + str(suffix)
                if new_id not in conflicts:
                    team_id = new_id
                    break
                suffix += 1

        if course_user_group is None:
            course_user_group, __ = CourseUserGroup.create(team_id, course_id, group_type=CourseUserGroup.TEAM)

        course_team, __ = cls.objects.get_or_create(
            course_user_group=course_user_group,
            defaults={
                'name': team_name,
                'topic_id': topic_id if topic_id else '',
                'description': description,
                'country': country if country else '',
                'language': language if language else '',
            }
        )

        return course_team
