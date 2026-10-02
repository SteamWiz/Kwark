from unittest.mock import Mock, patch
from wizlib.test_case import WizLibTestCase
from wizlib.config_handler import ConfigHandler

from kwark import KwarkApp
from test import MockAI, patch_ai_service


class TestCommandRize(WizLibTestCase):

    def test_stream(self):
        a = KwarkApp()
        a.config = ConfigHandler.fake(kwark_api_anthropic_key='fake-api-key')
        with \
                self.patch_stream('Francys'), \
                self.patchout() as o, \
                patch_ai_service():
            a.parse_run('doc')
        o.seek(0)
        self.assertIn('Mock AI response', o.read())
