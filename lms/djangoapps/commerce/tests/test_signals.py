"""
Tests for signal handling in commerce djangoapp.
"""
from django.test import TestCase
from django.test.utils import override_settings

import mock
from opaque_keys.edx.keys import CourseKey
from student.models import UNENROLL_DONE
from student.tests.factories import UserFactory, CourseEnrollmentFactory

from commerce.signals import refund_seat
from commerce.tests import TEST_API_URL, TEST_API_SIGNING_KEY
from commerce.tests.mocks import mock_create_refund


@override_settings(ECOMMERCE_API_URL=TEST_API_URL, ECOMMERCE_API_SIGNING_KEY=TEST_API_SIGNING_KEY)
class TestRefundSignal(TestCase):
    """
    Exercises logic triggered by the UNENROLL_DONE signal.
    """

    def setUp(self):
        super(TestRefundSignal, self).setUp()
        self.requester = UserFactory(username="test-requester")
        self.student = UserFactory(username="test-student")
        self.course_enrollment = CourseEnrollmentFactory(
            user=self.student,
            course_id=CourseKey.from_string('course-v1:org+course+run'),
        )
        self.course_enrollment.refundable = mock.Mock(return_value=True)

    def send_signal(self, skip_refund=False):
        """
        DRY helper: emit the UNENROLL_DONE signal, as is done in
        common.djangoapps.student.models after a successful unenrollment.
        """
        UNENROLL_DONE.send(sender=None, course_enrollment=self.course_enrollment, skip_refund=skip_refund)

    @override_settings(ECOMMERCE_API_URL=None, ECOMMERCE_API_SIGNING_KEY=None)
    def test_no_service(self):
        """
        Ensure that the receiver quietly bypasses attempts to initiate
        refunds when there is no external service configured.
        """
        with mock.patch('commerce.signals.refund_seat') as mock_refund_seat:
            self.send_signal()
            self.assertFalse(mock_refund_seat.called)

    @mock.patch('commerce.signals.refund_seat')
    def test_receiver(self, mock_refund_seat):
        """
        Ensure that the UNENROLL_DONE signal triggers correct calls to
        refund_seat(), when it is appropriate to do so.

        TODO (jsa): ideally we would assert that the signal receiver got wired
        up independently of the import statement in this module.  I'm not aware
        of any reliable / sane way to do this.
        """
        self.send_signal()
        self.assertTrue(mock_refund_seat.called)
        self.assertEqual(mock_refund_seat.call_args[0], (self.course_enrollment, self.student))

        # if skip_refund is set to True in the signal, we should not try to initiate a refund.
        mock_refund_seat.reset_mock()
        self.send_signal(skip_refund=True)
        self.assertFalse(mock_refund_seat.called)

        # if the course_enrollment is not refundable, we should not try to initiate a refund.
        mock_refund_seat.reset_mock()
        self.course_enrollment.refundable = mock.Mock(return_value=False)
        self.send_signal()
        self.assertFalse(mock_refund_seat.called)

    @mock.patch('commerce.signals.refund_seat')
    @mock.patch('commerce.signals.get_request_user', return_value=None)
    def test_requester(self, mock_get_request_user, mock_refund_seat):
        """
        Ensure the right requester is specified when initiating refunds.
        """
        # no HTTP request/user: auth to commerce service as the unenrolled student.
        self.send_signal()
        self.assertTrue(mock_refund_seat.called)
        self.assertEqual(mock_refund_seat.call_args[0], (self.course_enrollment, self.student))

        # HTTP user is the student: auth to commerce service as the unenrolled student.
        mock_get_request_user.return_value = self.student
        mock_refund_seat.reset_mock()
        self.send_signal()
        self.assertTrue(mock_refund_seat.called)
        self.assertEqual(mock_refund_seat.call_args[0], (self.course_enrollment, self.student))

        # HTTP user is another user: auth to commerce service as the requester.
        mock_get_request_user.return_value = self.requester
        mock_refund_seat.reset_mock()
        self.send_signal()
        self.assertTrue(mock_refund_seat.called)
        self.assertEqual(mock_refund_seat.call_args[0], (self.course_enrollment, self.requester))

    @mock.patch('commerce.signals.log.warning')
    def test_not_authorized_warning(self, mock_log_warning):
        """
        Ensure that expected authorization issues are logged as warnings.
        """
        with mock_create_refund(status=403):
            refund_seat(self.course_enrollment, None)
            self.assertTrue(mock_log_warning.called)

    @mock.patch('commerce.signals.log.exception')
    def test_error_logging(self, mock_log_exception):
        """
        Ensure that unexpected Exceptions are logged as errors (but do not
        break program flow).
        """
        with mock_create_refund(status=500):
            self.send_signal()
            self.assertTrue(mock_log_exception.called)
