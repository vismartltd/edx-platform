"""
Views for custom API
"""
import logging
import csv
import io
import StringIO

from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework import renderers

from django.conf import settings
from django.http import HttpResponseNotFound, HttpResponseForbidden
from django.test.client import RequestFactory
from django.contrib.auth.models import User

from courseware import grades
from xmodule.modulestore.django import modulestore

log = logging.getLogger('edx.' + __name__)

class CsvRenderer(renderers.BaseRenderer):
    media_type = 'text/csv'
    format = 'csv'

    def render(self, data, media_type=None, renderer_context=None):
        output = StringIO.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        # convert row elements to unicode and encode as UTF-8
        # in 'str' type to bypass csv library ascii-only limitation
        for row in data:
            writer.writerow([unicode(s).encode("utf-8") for s in row])
        # decode UTF-8 data from 'str' type to unicode
        # then encode it again in target charset
        return output.getvalue().decode("utf-8").encode(self.charset)

@api_view(["GET"])
@renderer_classes((JSONRenderer, CsvRenderer))
def all_grades(request, *args, **kwargs):
    """
    Return grades of all users for all courses
    """
    if not has_valid_token(request):
        return HttpResponseForbidden()

    all_courses = modulestore().get_courses()

    all_user_grades = {}
    for user in User.objects.all():
        student_info = get_student_info(user, all_courses)
        all_user_grades[student_info['email']] = student_info

    if request.accepted_renderer.format == 'json':
        return Response(all_user_grades)

    rows = [["user_id", "email", "username", "first_name", "last_name", "date_joined", "last_login",
             "course_id", "course_display_name", "total_percent", "grade",
             "section_category", "section_percent"]]

    user_keys = ["user_id", "email", "username", "first_name", "last_name", "date_joined", "last_login"]

    for email in all_user_grades:
        student_info = all_user_grades[email]
        student_grades = student_info['grades']
        for course_id in student_grades:
            course_grades = student_grades[course_id]
            for category in course_grades['grade_breakdown']:
                row = [student_info[key] for key in user_keys]
                row.extend([
                    course_id,
                    course_grades['course_display_name'],
                    course_grades['percent'],
                    course_grades['grade'] or "",
                    category['category'],
                    category['percent'],
                    ])
                rows.append(row)

    return Response(rows)

@api_view(["GET"])
def user_grades(request, *args, **kwargs):
    """
    Return grades of particular user for all courses
    """
    if not has_valid_token(request):
        return HttpResponseForbidden()

    username = kwargs.pop('username')
    user = None
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return HttpResponseNotFound()

    student_info = get_student_info(user, modulestore().get_courses())
    return Response(student_info)

def has_valid_token(request):
    return request.QUERY_PARAMS.get('token', "") == settings.CUSTOM_API_TOKEN

def get_student_info(user, courses):
    student_info = {
        'user_id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'username': user.username,
        'date_joined': user.date_joined,
        'last_login': user.last_login,
        }
    student_grades = student_info.setdefault('grades', {})
    for course in courses:
        course_grades = grades_for_student(user, course)
        course_grades['course_display_name'] = get_metadata_field_value(
            course.editable_metadata_fields, 'display_name', "")
        student_grades[str(course.id)] = course_grades
    return student_info

def get_metadata_field_value(metadata_fields, field_name, default=None):
    field = metadata_fields[field_name]
    if field is not None:
        field_value = field['value']
        if field_value is not None:
            return field_value
    return default

def grades_for_student(student, course):
    request = RequestFactory().get('/')
    try:
        request.user = student
        # Grading calls problem rendering, which calls masquerading,
        # which checks session vars -- thus the empty session dict below.
        # It's not pretty, but untangling that is currently beyond the
        # scope of this feature.
        request.session = {}
        return grades.grade(student, request, course)
    except Exception as exc:  # pylint: disable=broad-except
        # Keep marching on even if this student couldn't be graded for
        # some reason, but log it for future reference.
        log.exception(
            'Cannot grade student %s (%s) in course %s because of exception: %s',
            student.username,
            student.id,
            course.id,
            exc.message
        )
