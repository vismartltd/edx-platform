"""
Signal handling functions for use with external commerce service.
"""
import logging

from django.dispatch import receiver
from ecommerce_api_client.exceptions import HttpClientError
from request_cache.middleware import RequestCache
from student.models import UNENROLL_DONE

from commerce import ecommerce_api_client, is_commerce_service_configured

log = logging.getLogger(__name__)


@receiver(UNENROLL_DONE)
def handle_unenroll_done(sender, course_enrollment=None, skip_refund=False, **kwargs):  # pylint: disable=unused-argument
    """
    Signal receiver for unenrollments, used to automatically initiate refunds
    when applicable.

    N.B. this signal is also consumed by lms.djangoapps.shoppingcart.
    """
    if not is_commerce_service_configured() or skip_refund:
        return

    if course_enrollment and course_enrollment.refundable():
        try:
            request_user = get_request_user() or course_enrollment.user
            refund_seat(course_enrollment, request_user)
        except:  # pylint: disable=bare-except
            # don't assume the signal was fired with `send_robust`.
            # avoid blowing up other signal handlers by gracefully
            # trapping the Exception and logging an error.
            log.exception(
                "Unexpected exception while attempting to initiate refund for user [%s], course [%s]",
                course_enrollment.user,
                course_enrollment.course_id,
            )


def get_request_user():
    """
    Helper to get the authenticated user from the current HTTP request (if
    applicable).

    If the requester of an unenrollment is not the same person as the student
    being unenrolled, we authenticate to the commerce service as the requester.
    """
    request = RequestCache.get_current_request()
    return getattr(request, 'user', None)


def refund_seat(course_enrollment, request_user):
    """
    Attempt to initiate a refund for any orders associated with the seat being
    unenrolled, using the commerce service.

    Arguments:
        course_enrollment (CourseEnrollment): a student enrollment
        request_user: the user as whom to authenticate to the commerce service
            when attempting to initiate the refund.

    Returns:
        A list of the external service's IDs for any refunds that were initiated
            (may be empty).

    Raises:
        exceptions.SlumberBaseException: for any unhandled HTTP error during
            communication with the commerce service.
        exceptions.Timeout: if the attempt to reach the commerce service timed
            out.

    """
    course_key_str = unicode(course_enrollment.course_id)
    unenrolled_user = course_enrollment.user

    try:
        refund_ids = ecommerce_api_client(request_user or unenrolled_user).refunds.post(
            course_id=course_key_str,
            username=unenrolled_user.username,
        )
    except HttpClientError, exc:
        if exc.response.status_code == 403 and request_user != unenrolled_user:
            # this is a known limitation; commerce service does not presently
            # support the case of a non-superusers initiating a refund on
            # behalf of another user.
            log.warning("User [%s] was not authorized to initiate a refund for user [%s] "
                        "upon unenrollment from course [%s]", request_user, unenrolled_user, course_key_str)
            return []
        else:
            # no other error is anticipated, so re-raise the Exception
            raise exc

    if refund_ids:
        # at least one refundable order was found.
        log.info(
            "Refund successfully opened for user [%s], course [%s]: %r",
            unenrolled_user.id,
            course_key_str,
            refund_ids,
        )
    else:
        # no refundable orders were found.
        log.debug("No refund opened for user [%s], course [%s]", unenrolled_user.id, course_key_str)

    return refund_ids
