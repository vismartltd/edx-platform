import logging
import random

from xmodule.x_module import XModule, STUDENT_VIEW, AUTHOR_VIEW
from xmodule.seq_module import SequenceDescriptor
from xmodule.studio_editable import StudioEditableModule, StudioEditableDescriptor

from lxml import etree

from xblock.fields import Scope, Integer, String, List
from xblock.fragment import Fragment

from django.test.client import RequestFactory
from courseware import grades
from courseware import courses
from student import models
from opaque_keys.edx.locator import CourseLocator
from copy import copy

log = logging.getLogger('edx.' + __name__)


class RandomizeFields(object):
    base_course_key = String(help="Course ID as grading source for additional questions", scope=Scope.settings)
    choices = List(help="Which random child was chosen", scope=Scope.user_state)

def grades_for_student(student, course_id):
    request = RequestFactory().get('/')
    course = courses.get_course_by_id(course_id)
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
            course_id,
            exc.message
        )


class RandomizeModule(RandomizeFields, XModule, StudioEditableModule):
    """
    Chooses a random child module.  Chooses the same one every time for each student.

     Example:
     <randomize>
     <problem url_name="problem1" />
     <problem url_name="problem2" />
     <problem url_name="problem3" />
     </randomize>

    User notes:

      - If you're randomizing amongst graded modules, each of them MUST be worth the same
        number of points.  Otherwise, the earth will be overrun by monsters from the
        deeps.  You have been warned.

    Technical notes:
      - There is more dark magic in this code than I'd like.  The whole varying-children +
        grading interaction is a tangle between super and subclasses of descriptors and
        modules.
"""
    def __init__(self, *args, **kwargs):
        super(RandomizeModule, self).__init__(*args, **kwargs)

        # NOTE: calling self.get_children() creates a circular reference--
        # it calls get_child_descriptors() internally, but that doesn't work until
        # we've picked a choice
        num_choices = len(self.descriptor.get_children())

        user = models.user_by_anonymous_id(self.system.anonymous_student_id)
        user_grades = None
        if user and self.base_course_key:
            course_key = CourseLocator.from_string(self.base_course_key)
            user_grades = grades_for_student(user, course_key)
            log.debug("Student %s grades for course %s: %s", user.id, course_key, user_grades)

        if not self.choices or any(choice >= num_choices for choice in self.choices):
            # Oops.  Children changed. Reset.
            self.choices = None

        if self.choices is None:
            # choose one based on the system seed, or randomly if that's not available
            if num_choices > 0 and user_grades is not None:
                # if self.system.seed is not None:
                #     self.choice = self.system.seed % num_choices
                # else:
                #     self.choice = random.randrange(0, num_choices)
                base_course_percent = user_grades['percent']
                question_count = 1 + int(round((1.0 - base_course_percent) * (num_choices - 1)))
                self.choices = random.sample(list(range(0, num_choices)), question_count)
                log.debug("chose %s questions of %s based on grade percent %s",
                          question_count, num_choices, base_course_percent)

        if self.choices is not None:
            descriptor_children = self.descriptor.get_children()
            self.child_descriptor = [descriptor_children[choice] for choice in self.choices]
            # Now get_children() should return a list with one element
            log.debug("children of randomize module (should be only 1): %s", self.get_children())
            self.child = self.get_children()
        else:
            self.child_descriptor = None
            self.child = None

    def max_score(self):
        if self.child_descriptor is None:
            return None

        return sum(map(lambda child: child.max_score(), self.get_children()))

    def get_child_descriptors(self):
        """
        For grading--return just the chosen child.
        """
        if self.child_descriptor is None:
            return []

        return self.child_descriptor

    def student_view(self, context):
        if self.child is None:
            # raise error instead?  In fact, could complain on descriptor load...
            return Fragment(content=u"<div>Nothing to randomize between</div>")

        #return self.child.render(STUDENT_VIEW, context)
        fragment = Fragment()
        contents = []

        child_context = {} if not context else copy(context)
        child_context['child_of_vertical'] = True

        for child in self.get_display_items():
            rendered_child = child.render(STUDENT_VIEW, child_context)
            fragment.add_frag_resources(rendered_child)

            contents.append({
                'id': child.location.to_deprecated_string(),
                'content': rendered_child.content
            })

        fragment.add_content(self.system.render_template('vert_module.html', {
            'items': contents,
            'xblock_context': context,
        }))
        return fragment

    def author_view(self, context):
        """
        Renders the Studio preview view, which supports drag and drop.
        """
        fragment = Fragment()
        self.render_children(context, fragment, can_reorder=True, can_add=True)
        return fragment

    def get_icon_class(self):
        #return self.child.get_icon_class() if self.child else 'other'
        return 'other'


class RandomizeDescriptor(RandomizeFields, SequenceDescriptor, StudioEditableDescriptor):
    # the editing interface can be the same as for sequences -- just a container
    module_class = RandomizeModule

    filename_extension = "xml"

    def definition_to_xml(self, resource_fs):

        xml_object = etree.Element('randomize')
        for child in self.get_children():
            self.runtime.add_block_as_child_node(child, xml_object)
        return xml_object

    def has_dynamic_children(self):
        """
        Grading needs to know that only one of the children is actually "real".  This
        makes it use module.get_child_descriptors().
        """
        return True
