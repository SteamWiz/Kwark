import os
import tempfile
from unittest.mock import Mock, patch, call

from wizlib.test_case import WizLibTestCase
from wizlib.config_handler import ConfigHandler

from kwark import KwarkApp
from kwark.util import parse_yaml_input
from kwark.ai_services.anthropic_ai_service import (
    AnthropicMessagesBlock,
    file_content_type,
)
from test import patch_ai_service


class TestFileUploadActivateCommand(WizLibTestCase):

    # --- parse_yaml_input tests ---

    def test_yaml_with_file_key(self):
        """parse_yaml_input extracts file path."""
        y = "prompt: Summarize\nfile: /tmp/doc.pdf"
        r = parse_yaml_input(y)
        self.assertEqual('/tmp/doc.pdf', r['file'])
        self.assertEqual('Summarize', r['prompt'])

    def test_yaml_without_file_key(self):
        """parse_yaml_input returns None for file."""
        y = "prompt: Hello"
        r = parse_yaml_input(y)
        self.assertIsNone(r['file'])

    def test_yaml_file_only(self):
        """parse_yaml_input with file but no prompt."""
        y = "file: /tmp/doc.pdf"
        r = parse_yaml_input(y)
        self.assertEqual('/tmp/doc.pdf', r['file'])
        self.assertIsNone(r['prompt'])

    def test_plain_text_no_file(self):
        """Plain text input has no file."""
        r = parse_yaml_input("just text")
        self.assertIsNone(r['file'])

    # --- AnthropicMessagesBlock tests ---

    def test_user_says_with_file_id(self):
        """user_says with file_id includes document block."""
        m = AnthropicMessagesBlock()
        m.user_says("Summarize", file_id="file_abc")
        msg = m[0]
        self.assertEqual("user", msg["role"])
        c = msg["content"]
        self.assertEqual(2, len(c))
        self.assertEqual("document", c[0]["type"])
        self.assertEqual("file", c[0]["source"]["type"])
        self.assertEqual(
            "file_abc", c[0]["source"]["file_id"])
        self.assertEqual("text", c[1]["type"])
        self.assertEqual("Summarize", c[1]["text"])

    def test_user_says_with_image_file_type(self):
        """user_says with file_type='image' sets type."""
        m = AnthropicMessagesBlock()
        m.user_says(
            "Describe", file_id="file_img",
            file_type="image")
        c = m[0]["content"]
        self.assertEqual("image", c[0]["type"])

    def test_user_says_without_file_id(self):
        """user_says without file_id is plain text."""
        m = AnthropicMessagesBlock()
        m.user_says("Hello")
        msg = m[0]
        self.assertEqual("user", msg["role"])
        self.assertEqual("Hello", msg["content"])

    # --- file_content_type tests ---

    def test_file_content_type_pdf(self):
        """PDF maps to document."""
        self.assertEqual(
            "document", file_content_type("/a/b.pdf"))

    def test_file_content_type_png(self):
        """PNG maps to image."""
        self.assertEqual(
            "image", file_content_type("/a/photo.png"))

    def test_file_content_type_jpg(self):
        """JPG maps to image."""
        self.assertEqual(
            "image", file_content_type("pic.jpg"))

    def test_file_content_type_unknown(self):
        """Unknown extension defaults to document."""
        self.assertEqual(
            "document", file_content_type("data.xyz"))

    # --- Activate command integration tests ---

    def test_activate_with_file_uploads_and_deletes(self):
        """Activate uploads file, queries with file_id,
        and deletes file."""
        with patch(
                'sys.stdin.isatty', return_value=True):
            a = KwarkApp()
            a.config = ConfigHandler.fake(
                kwark_api_anthropic_key='k')

        m = Mock()
        mi = Mock()
        mi.query_with_tools_ui.return_value = 'Response'
        mi.upload_file.return_value = 'file_abc'
        m.return_value = mi

        with tempfile.NamedTemporaryFile(
                mode='w', suffix='.txt',
                delete=False) as f:
            f.write('content')
            fp = f.name

        y = f"prompt: Summarize\nfile: {fp}"
        try:
            with \
                    self.patch_stream(y), \
                    self.patchout() as o, \
                    self.patcherr(), \
                    patch_ai_service(m):
                a.parse_run('activate')

            o.seek(0)
            self.assertEqual(
                'Response', o.read().strip())

            mi.upload_file.assert_called_once_with(fp)

            c = mi.query_with_tools_ui.call_args
            self.assertEqual(
                'file_abc', c[1].get('file_id'))
            self.assertEqual(
                'document', c[1].get('file_type'))

            mi.delete_file.assert_called_once_with(
                'file_abc')
        finally:
            os.unlink(fp)

    def test_activate_with_image_passes_image_type(self):
        """Activate with .png file passes file_type=image."""
        with patch(
                'sys.stdin.isatty', return_value=True):
            a = KwarkApp()
            a.config = ConfigHandler.fake(
                kwark_api_anthropic_key='k')

        m = Mock()
        mi = Mock()
        mi.query_with_tools_ui.return_value = 'Described'
        mi.upload_file.return_value = 'file_img'
        m.return_value = mi

        with tempfile.NamedTemporaryFile(
                mode='wb', suffix='.png',
                delete=False) as f:
            f.write(b'\x89PNG')
            fp = f.name

        y = f"prompt: Describe this\nfile: {fp}"
        try:
            with \
                    self.patch_stream(y), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(m):
                a.parse_run('activate')

            c = mi.query_with_tools_ui.call_args
            self.assertEqual(
                'image', c[1].get('file_type'))
        finally:
            os.unlink(fp)

    def test_activate_deletes_file_on_error(self):
        """File is deleted even when query raises."""
        with patch(
                'sys.stdin.isatty', return_value=True):
            a = KwarkApp()
            a.config = ConfigHandler.fake(
                kwark_api_anthropic_key='k')

        m = Mock()
        mi = Mock()
        mi.query_with_tools_ui.side_effect = (
            RuntimeError('limit exceeded'))
        mi.upload_file.return_value = 'file_xyz'
        m.return_value = mi

        with tempfile.NamedTemporaryFile(
                mode='w', suffix='.txt',
                delete=False) as f:
            f.write('content')
            fp = f.name

        y = f"prompt: Summarize\nfile: {fp}"
        try:
            with \
                    self.patch_stream(y), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(m):
                a.parse_run('activate')

            mi.delete_file.assert_called_once_with(
                'file_xyz')
        finally:
            os.unlink(fp)

    def test_activate_without_file_no_upload(self):
        """Activate without file does not call upload."""
        with patch(
                'sys.stdin.isatty', return_value=True):
            a = KwarkApp()
            a.config = ConfigHandler.fake(
                kwark_api_anthropic_key='k')

        m = Mock()
        mi = Mock()
        mi.query_with_tools_ui.return_value = 'OK'
        m.return_value = mi

        y = "prompt: Hello"
        with \
                self.patch_stream(y), \
                self.patchout(), \
                self.patcherr(), \
                patch_ai_service(m):
            a.parse_run('activate')

        mi.upload_file.assert_not_called()
        mi.delete_file.assert_not_called()

        c = mi.query_with_tools_ui.call_args
        self.assertIsNone(c[1].get('file_id'))
