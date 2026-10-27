from django.test import TestCase
from django.urls import reverse


class CoreViewsTests(TestCase):
    
    def test_index_view_renders_successfully(self):
        response = self.client.get(reverse('core:index'))
        self.assertEqual(response.status_code, 200)
