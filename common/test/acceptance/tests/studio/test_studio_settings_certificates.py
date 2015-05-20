"""
Acceptance tests for Studio's Setting pages
"""
from .base_studio_test import StudioCourseTest
from ...pages.studio.settings_certificates import CertificatesPage


class CertificatesTest(StudioCourseTest):
    """
    Tests for settings/certificates Page.
    """
    def setUp(self, is_staff=False):
        super(CertificatesTest, self).setUp(is_staff)
        self.certificates_page = CertificatesPage(
            self.browser,
            self.course_info['org'],
            self.course_info['number'],
            self.course_info['run']
        )

    def make_signatory_data(self, prefix='First'):
        """
        Makes signatory dict which can be used in the tests to create certificates
        """
        return {
            'name': '{prefix} Signatory Name'.format(prefix=prefix),
            'title': '{prefix} Signatory Title'.format(prefix=prefix),
            'organization': '{prefix} Signatory Organization'.format(prefix=prefix),
        }

    def create_and_verify_certificate(self, name, description, existing_certs, signatories):
        """
        Creates a new certificate and verifies that it was properly created.
        """
        self.assertEqual(existing_certs, len(self.certificates_page.certificates))
        if existing_certs == 0:
            self.certificates_page.create_first_certificate()
        else:
            self.certificates_page.add_certificate()
        certificate = self.certificates_page.certificates[existing_certs]
        certificate.name = name
        certificate.description = description

        # add signatories
        added_signatories = 0
        for idx, signatory in enumerate(signatories):
            certificate.signatories[idx].name = signatory['name']
            certificate.signatories[idx].title = signatory['title']
            certificate.signatories[idx].organization = signatory['organization']
            certificate.signatories[idx].upload_signature_image('Signature-{}.png'.format(idx))
            self.assertTrue(certificate.signatories[idx].signature_image_is_present)

            added_signatories += 1
            if len(signatories) > added_signatories:
                certificate.add_signatory()

        # Save the certificate
        self.assertEqual(certificate.get_text('.action-primary'), "Create")
        self.assertFalse(certificate.delete_button_is_present)
        certificate.save()
        self.assertIn(name, certificate.name)
        return certificate

    def test_no_certificates_by_default(self):
        """
        Scenario: Ensure that message telling me to create a new certificate is
            shown when no certificate exist.
        Given I have a course without certificates
        When I go to the Certificates page in Studio
        Then I see "You have not created any certificates yet." message
        """
        self.certificates_page.visit()
        self.assertTrue(self.certificates_page.no_certificates_message_shown)
        self.assertIn(
            "You have not created any certificates yet.",
            self.certificates_page.no_certificates_message_text
        )

    def test_can_create_and_edit_certficates(self):
        """
        Scenario: Ensure that the certificates can be created and edited correctly.
        Given I have a course without certificates
        When I click button 'Add your first Certificate'
        And I set new the name, description and two signatories and click the button 'Create'
        Then I see the new certificate is added and has correct data
        And I click 'New Certificate' button
        And I set the name and click the button 'Create'
        Then I see the second certificate is added and has correct data
        When I edit the second certificate
        And I change the name and click the button 'Save'
        Then I see the second certificate is saved successfully and has the new name
        """
        self.certificates_page.visit()
        self.create_and_verify_certificate(
            "New Certificate",
            "Description of first certificate",
            0,
            [self.make_signatory_data('first'), self.make_signatory_data('second')]
        )
        second_certificate = self.create_and_verify_certificate(
            "Second Certificate",
            "Description of first certificate",
            1,
            [self.make_signatory_data('third'), self.make_signatory_data('forth')]
        )

        # Edit the second certificate
        second_certificate.edit()
        second_certificate.name = "Updated Second Certificate"
        self.assertEqual(second_certificate.get_text('.action-primary'), "Save")
        second_certificate.save()

        self.assertIn("Updated Second Certificate", second_certificate.name)

    def test_can_delete_certificate(self):
        """
        Scenario: Ensure that the user can delete certificate.
        Given I have a course with 1 certificate
        And I go to the Certificates page
        When I delete the Certificate with name "New Certificate"
        Then I see that there is no certificate
        When I refresh the page
        Then I see that the certificate has been deleted
        """
        self.certificates_page.visit()
        certificate = self.create_and_verify_certificate(
            "New Certificate",
            "Description of first certificate",
            0,
            [self.make_signatory_data('first'), self.make_signatory_data('second')]
        )

        self.assertTrue(certificate.delete_button_is_present)

        self.assertEqual(len(self.certificates_page.certificates), 1)

        # Delete certificate
        certificate.delete_certificate()

        self.certificates_page.visit()
        self.assertEqual(len(self.certificates_page.certificates), 0)

    def test_can_create_and_edit_signatories_of_certficate(self):
        """
        Scenario: Ensure that the certificates can be created with signatories and edited correctly.
        Given I have a course without certificates
        When I click button 'Add your first Certificate'
        And I set new the name, description and signatory and click the button 'Create'
        Then I see the new certificate is added and has one signatory inside it
        When I click 'Edit' button of signatory panel
        And I set the name and click the button 'Save' icon
        Then I see the signatory name updated with newly set name
        When I refresh the certificates page
        Then I can see course has one certificate with new signatory name
        When I click 'Edit' button of signatory panel
        And click on 'Close' button
        Then I can see no change in signatory detail
        """
        self.certificates_page.visit()
        certificate = self.create_and_verify_certificate(
            "New Certificate",
            "Description of first certificate",
            0,
            [self.make_signatory_data('first')]
        )
        self.assertEqual(len(self.certificates_page.certificates), 1)
        # Edit the signatory in certificate
        signatory = certificate.signatories[0]
        signatory.edit()

        signatory.name = 'Updated signatory name'
        signatory.title = 'Update signatory title'
        signatory.organization = 'Updated signatory organization'
        signatory.save()

        self.assertEqual(len(self.certificates_page.certificates), 1)

        signatory = self.certificates_page.certificates[0].signatories[0]
        self.assertIn("Updated signatory name", signatory.name)
        self.assertIn("Update signatory title", signatory.title)
        self.assertIn("Updated signatory organization", signatory.organization)

        signatory.edit()
        signatory.close()

        self.assertIn("Updated signatory name", signatory.name)

    def test_must_supply_certificate_name(self):
        """
        Scenario: Ensure that validation of the certificates works correctly.
        Given I have a course without certificates
        And I create new certificate without specifying a name click the button 'Create'
        Then I see error message "Certificate name is required."
        When I set a name and click the button 'Create'
        Then I see the certificate is saved successfully
        """
        self.certificates_page.visit()
        self.certificates_page.create_first_certificate()
        certificate = self.certificates_page.certificates[0]
        certificate.name = ""
        certificate.save()
        self.assertEqual(certificate.mode, 'edit')
        self.assertEqual("Certificate name is required.", certificate.validation_message)
        certificate.name = "First Certificate Name"
        certificate.save()
        self.assertIn("First Certificate Name", certificate.name)

    def test_can_cancel_creation_of_certificate(self):
        """
        Scenario: Ensure that creation of a certificate can be canceled correctly.
        Given I have a course without certificates
        When I click button 'Add your first Certificate'
        And I set name of certificate and click the button 'Cancel'
        Then I see that there is no certificates in the course
        """
        self.certificates_page.visit()
        self.certificates_page.create_first_certificate()
        certificate = self.certificates_page.certificates[0]
        certificate.name = "First Certificate Name"
        certificate.cancel()
        self.assertEqual(len(self.certificates_page.certificates), 0)
