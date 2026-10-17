from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from feature_flags.models import FeatureFlag
from feature_flags.services import invalidate_flag_cache
from .models import StartupMilestone, StartupProject

User = get_user_model()


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


class StartupWorkspaceAPITests(APITestCase):
    def setUp(self):
        FeatureFlag.objects.update_or_create(key='startup_tools', defaults={'is_enabled': True})
        invalidate_flag_cache('startup_tools')
        self.owner = User.objects.create_user(
            username='project-owner', email='owner@example.com', password='Password123!',
        )
        self.other_user = User.objects.create_user(
            username='other-project-owner', email='other@example.com', password='Password123!',
        )
        self.project = StartupProject.objects.create(owner=self.owner, title='My startup')
        self.other_project = StartupProject.objects.create(owner=self.other_user, title='Private startup')
        self.milestone = StartupMilestone.objects.create(project=self.project, title='Interview customers')

    def tearDown(self):
        invalidate_flag_cache('startup_tools')

    def test_project_api_requires_authentication(self):
        FeatureFlag.objects.filter(key='startup_tools').update(is_enabled=False)
        invalidate_flag_cache('startup_tools')
        response = self.client.get(reverse('startup-project-list'))
        self.assertIn(response.status_code, (401, 403))

    def test_disabled_flag_hides_workspace_api_from_authenticated_users(self):
        FeatureFlag.objects.filter(key='startup_tools').update(is_enabled=False)
        invalidate_flag_cache('startup_tools')
        self.client.force_authenticate(self.owner)

        project_response = self.client.get(reverse('startup-project-list'))
        milestone_response = self.client.get(reverse('startup-milestone-list'))
        project_create_response = self.client.post(
            reverse('startup-project-list'),
            {'title': 'Blocked venture'},
            format='json',
        )
        milestone_create_response = self.client.post(
            reverse('startup-milestone-list'),
            {'project': self.project.id, 'title': 'Blocked milestone'},
            format='json',
        )

        self.assertEqual(project_response.status_code, 404)
        self.assertEqual(milestone_response.status_code, 404)
        self.assertEqual(project_create_response.status_code, 404)
        self.assertEqual(milestone_create_response.status_code, 404)
        self.assertFalse(StartupProject.objects.filter(title='Blocked venture').exists())
        self.assertFalse(StartupMilestone.objects.filter(title='Blocked milestone').exists())

    def test_enabled_flag_allows_workspace_api(self):
        FeatureFlag.objects.filter(key='startup_tools').update(is_enabled=True)
        invalidate_flag_cache('startup_tools')
        self.client.force_authenticate(self.owner)

        project_response = self.client.get(reverse('startup-project-list'))
        milestone_response = self.client.get(reverse('startup-milestone-list'))

        self.assertEqual(project_response.status_code, 200)
        self.assertEqual(milestone_response.status_code, 200)
        self.assertEqual([item['id'] for item in project_response.data], [self.project.id])
        self.assertEqual([item['id'] for item in milestone_response.data], [self.milestone.id])

    def test_project_list_only_returns_the_authenticated_users_projects(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get(reverse('startup-project-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data], [self.project.id])
        self.assertEqual(response.data[0]['milestones'][0]['id'], self.milestone.id)

    def test_project_create_assigns_owner_from_authentication_not_request_data(self):
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            reverse('startup-project-list'),
            {'title': 'New venture', 'owner': self.other_user.id},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['owner'], self.owner.id)
        self.assertFalse(StartupProject.objects.filter(title='New venture', owner=self.other_user).exists())

    def test_users_cannot_retrieve_or_update_another_users_project(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get(reverse('startup-project-detail', args=[self.other_project.id]))
        self.assertEqual(response.status_code, 404)

        response = self.client.patch(
            reverse('startup-project-detail', args=[self.other_project.id]),
            {'title': 'Changed title'},
            format='json',
        )
        self.assertEqual(response.status_code, 404)
        self.other_project.refresh_from_db()
        self.assertEqual(self.other_project.title, 'Private startup')

    def test_user_cannot_create_milestone_for_another_users_project(self):
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            reverse('startup-milestone-list'),
            {'project': self.other_project.id, 'title': 'Unauthorized milestone'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(StartupMilestone.objects.filter(title='Unauthorized milestone').exists())

    def test_milestone_list_is_limited_to_projects_owned_by_the_user(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get(reverse('startup-milestone-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data], [self.milestone.id])

    def test_workspace_endpoints_do_not_expose_delete_operations(self):
        self.client.force_authenticate(self.owner)

        project_response = self.client.delete(reverse('startup-project-detail', args=[self.project.id]))
        milestone_response = self.client.delete(reverse('startup-milestone-detail', args=[self.milestone.id]))

        self.assertEqual(project_response.status_code, 405)
        self.assertEqual(milestone_response.status_code, 405)
        self.assertTrue(StartupProject.objects.filter(id=self.project.id).exists())
        self.assertTrue(StartupMilestone.objects.filter(id=self.milestone.id).exists())
