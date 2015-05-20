"""
Django models related to teams functionality.
"""

from django.contrib.auth.models import User
from django.db import models
from .utils import slugify

from xmodule_django.models import CourseKeyField

class CourseTeam(models.Model):
    """
    This model represents team related info.
    """

    class Meta:
        unique_together = (('team_id', 'course_id'),)

    team_id = models.CharField(max_length=100, db_index=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    course_id = CourseKeyField(max_length=255, db_index=True)
    topic_id = models.CharField(max_length=100, db_index=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    # last_activity is computed through a query
    description = models.CharField(max_length=1000)
    country = models.CharField(max_length=50, blank=True)
    language = models.CharField(max_length=20, blank=True)
    users = models.ManyToManyField(User, db_index=True, related_name='teams', through='CourseTeamMembership')

    @classmethod
    def create(cls, name, course_id, description, topic_id=None, country=None, language=None):
        """
        Create a complete (CourseUserGroup + CourseTeam) object.

        Args:
            name: Name of the team to be created
            course_id: Course id
            description: Description of the team
            topic_id: Identifier for the topic the team formed around
            course_user_group: CourseUserGroup
            country: Country where the team is based
            language: Language the team uses
        """

        team_id = slugify(name)
        conflicts = cls.objects.filter(team_id__startswith=team_id).values_list('team_id', flat=True)

        if conflicts and team_id in conflicts:
            suffix = 2
            while True:
                new_id = team_id + '-' + str(suffix)
                if new_id not in conflicts:
                    team_id = new_id
                    break
                suffix += 1

        course_team = cls.objects.create(
            team_id=team_id,
            name=name,
            course_id=course_id,
            topic_id=topic_id if topic_id else '',
            description=description,
            country=country if country else '',
            language=language if language else '',
        )

        return course_team


class CourseTeamMembership(models.Model):
    """
    This model represents the membership of a single user in a single team.
    """

    class Meta:
        unique_together = (('user', 'team'),)

    user = models.ForeignKey(User)
    team = models.ForeignKey(CourseTeam)
    date_joined = models.DateTimeField(auto_now_add=True)
