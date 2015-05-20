"""
Views related to operations on course objects
"""
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_GET
from django.core.exceptions import PermissionDenied
from openedx.core.djangoapps.credit.api import get_credit_requirements
from edxmako.shortcuts import render_to_response

from xmodule.modulestore.django import modulestore
from opaque_keys.edx.keys import CourseKey

from django_future.csrf import ensure_csrf_cookie
from student.auth import has_course_author_access

__all__ = ['credit_eligibility_handler', ]


# pylint: disable=unused-argument
@ensure_csrf_cookie
@require_http_methods("GET")
@login_required
def credit_eligibility_handler(request, course_key_string):
    """
    The restful handler for checklists.

    GET
        html: return html page for all checklists
        json: return json representing all checklists. checklist_index is not supported for GET at this time.
    POST or PUT
        json: updates the checked state for items within a particular checklist. checklist_index is required.
    """

    course_key = CourseKey.from_string(course_key_string)
    if not has_course_author_access(request.user, course_key):
        raise PermissionDenied()

    course_module = modulestore().get_course(course_key)

    json_request = 'application/json' in request.META.get('HTTP_ACCEPT', 'application/json')
    if request.method == 'GET':
        # If course was created before checklists were introduced, copy them over
        # from the template.

        requirements = get_credit_requirements(course_key)
        return render_to_response('credit_eligibility.html',
                                  {
                                      'requirements': requirements,
                                      'context_course': course_module,
                                  })