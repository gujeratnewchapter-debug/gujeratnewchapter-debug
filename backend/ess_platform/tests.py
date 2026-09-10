from django.test import TestCase
from django.urls import reverse


class ServiceRequestTests(TestCase):
    def test_anonymous_visitor_can_submit_service_request(self):
        response = self.client.post(
            reverse('service-request-list'),
            {'service': 'Market Research', 'notes': 'I need help validating a customer problem.'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)

    def test_anonymous_visitor_cannot_read_service_requests(self):
        response = self.client.get(reverse('service-request-list'))

        self.assertEqual(response.status_code, 403)
