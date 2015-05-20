"""
Signal handling functions for use with external commerce service.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from django.utils.translation import ugettext as _
from ecommerce_api_client.exceptions import HttpClientError
from microsite_configuration import microsite
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
        try:
            send_refund_notification(course_enrollment, refund_ids)
        except:  # pylint: disable=bare-except
            # don't break, just log a warning
            log.warning("Could not send email notification for refund.", exc_info=True)
    else:
        # no refundable orders were found.
        log.debug("No refund opened for user [%s], course [%s]", unenrolled_user.id, course_key_str)

    return refund_ids


def send_refund_notification(course_enrollment, refund_ids):
    """
    Issue an email notification to the configured email recipient about a
    newly-initiated refund request.

    This function does not do any exception handling; callers are responsible
    for capturing and recovering from any errors.
    """
    if microsite.is_request_in_microsite():
        # this is not presently supported with the external service.
        raise NotImplementedError("Unable to send refund processing emails to microsite teams.")

    for_user = course_enrollment.user
    subject = _("[Refund] User-Requested Refund")
    message = _("A refund request has been initiated for {0} ({1}). "
                "To process this request, please visit the link(s) below.").format(for_user, for_user.email)

    refund_urls = ["{}/dashboard/refunds/{}/".format(settings.ECOMMERCE_API_URL, refund_id) for refund_id in refund_ids]
    text_body = '\r\n'.join([message] + refund_urls + [''])
    refund_links = ['<a href="{0}">{0}</a>'.format(url) for url in refund_urls]
    html_body = '<p>{0}</p>'.format('<br>'.join([message] + refund_links))

    to_email = settings.PAYMENT_SUPPORT_EMAIL
    from_email = settings.PAYMENT_SUPPORT_EMAIL

    email_message = EmailMultiAlternatives(subject, text_body, from_email, [to_email])
    email_message.attach_alternative(html_body, "text/html")
    email_message.send()
