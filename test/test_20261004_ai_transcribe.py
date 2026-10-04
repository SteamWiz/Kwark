"""kwark.ai.transcribe() turns a file into Markdown (library layer)"""
import base64
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

import anthropic
import httpx

from kwark.ai import APIError
from kwark.ai import KwarkAIError
from kwark.ai import TRANSCRIBE_DISCLAIMER
from kwark.ai import TRANSCRIBE_PROMPT
from kwark.ai import TruncatedResponseError
from kwark.ai import UnsupportedFileTypeError
from kwark.ai import transcribe


ANTHROPIC = 'kwark.ai.transcription.Anthropic'
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def text_block(text):
    return SimpleNamespace(type='text', text=text)


def fake_message(content=None, stop_reason='end_turn'):
    if content is None:
        content = [text_block('# Hello')]
    return SimpleNamespace(content=content, stop_reason=stop_reason)


def mock_client(message=None, error=None):
    """Return a mock Anthropic class whose client streams the message"""
    client = MagicMock()
    stream = MagicMock()
    stream.get_final_message.return_value = message or fake_message()
    manager = client.messages.stream.return_value
    manager.__enter__.return_value = stream
    manager.__exit__.return_value = False
    if error:
        client.messages.stream.side_effect = error
    return MagicMock(return_value=client), client


class TestTranscribe(TestCase):

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.dir = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def make_file(self, name, data):
        path = self.dir / name
        if isinstance(data, str):
            path.write_text(data, encoding='utf-8')
        else:
            path.write_bytes(data)
        return path

    def run_transcribe(self, path, message=None, **kwargs):
        anthropic_class, client = mock_client(message)
        with patch(ANTHROPIC, anthropic_class):
            result = transcribe(path, **kwargs)
        return result, anthropic_class, client

    def sent_content(self, client):
        kwargs = client.messages.stream.call_args.kwargs
        return kwargs['messages'][0]['content']

    def test_pdf(self):
        path = self.make_file('doc.pdf', b'%PDF-1.4 fake')
        result, _, client = self.run_transcribe(path)
        self.assertEqual('# Hello', result)
        file_block, prompt_block = self.sent_content(client)
        self.assertEqual({
            'type': 'document',
            'source': {
                'type': 'base64',
                'media_type': 'application/pdf',
                'data': base64.standard_b64encode(
                    b'%PDF-1.4 fake').decode('ascii')}}, file_block)
        self.assertEqual({'type': 'text', 'text': TRANSCRIBE_PROMPT},
                         prompt_block)

    def test_images(self):
        cases = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
        }
        for suffix, media_type in cases.items():
            with self.subTest(suffix=suffix):
                path = self.make_file('pic' + suffix, b'\x89binary')
                _, _, client = self.run_transcribe(path)
                file_block = self.sent_content(client)[0]
                self.assertEqual('image', file_block['type'])
                self.assertEqual('base64', file_block['source']['type'])
                self.assertEqual(media_type,
                                 file_block['source']['media_type'])
                self.assertEqual(
                    base64.standard_b64encode(b'\x89binary').decode(),
                    file_block['source']['data'])

    def test_text_files(self):
        for suffix in ['.txt', '.md', '.csv']:
            with self.subTest(suffix=suffix):
                path = self.make_file('notes' + suffix, 'a,b\n1,ü\n')
                _, _, client = self.run_transcribe(path)
                file_block = self.sent_content(client)[0]
                self.assertEqual({
                    'type': 'document',
                    'source': {
                        'type': 'text',
                        'media_type': 'text/plain',
                        'data': 'a,b\n1,ü\n'}}, file_block)

    def test_upper_case_suffix(self):
        path = self.make_file('SCAN.JPG', b'img')
        _, _, client = self.run_transcribe(path)
        file_block = self.sent_content(client)[0]
        self.assertEqual('image', file_block['type'])
        self.assertEqual('image/jpeg', file_block['source']['media_type'])

    def test_accepts_str_path(self):
        path = self.make_file('doc.txt', 'hi')
        result, _, _ = self.run_transcribe(str(path))
        self.assertEqual('# Hello', result)

    def test_unsupported_type(self):
        path = self.make_file('archive.zip', b'PK')
        anthropic_class, _ = mock_client()
        with patch(ANTHROPIC, anthropic_class):
            with self.assertRaises(UnsupportedFileTypeError) as ctx:
                transcribe(path)
        self.assertIsInstance(ctx.exception, KwarkAIError)
        self.assertIn('.zip', str(ctx.exception))
        anthropic_class.assert_not_called()

    def test_no_suffix_unsupported(self):
        path = self.make_file('README', 'text')
        anthropic_class, _ = mock_client()
        with patch(ANTHROPIC, anthropic_class):
            with self.assertRaises(UnsupportedFileTypeError):
                transcribe(path)
        anthropic_class.assert_not_called()

    def test_max_tokens_raises(self):
        path = self.make_file('doc.md', 'long')
        message = fake_message(stop_reason='max_tokens')
        with self.assertRaises(TruncatedResponseError) as ctx:
            self.run_transcribe(path, message=message, max_tokens=100)
        self.assertIsInstance(ctx.exception, KwarkAIError)
        self.assertIn('max_tokens', str(ctx.exception))

    def test_joins_text_blocks_only(self):
        path = self.make_file('doc.txt', 'x')
        message = fake_message(content=[
            text_block('# Title\n'),
            SimpleNamespace(type='thinking', thinking='hmm'),
            text_block('Body')])
        result, _, _ = self.run_transcribe(path, message=message)
        self.assertEqual('# Title\nBody', result)

    def test_disclaimer_not_added(self):
        path = self.make_file('doc.txt', 'x')
        result, _, _ = self.run_transcribe(path)
        self.assertNotIn(TRANSCRIBE_DISCLAIMER, result)

    def test_defaults_passed_through(self):
        path = self.make_file('doc.txt', 'x')
        _, anthropic_class, client = self.run_transcribe(path)
        anthropic_class.assert_called_once_with(api_key=None)
        kwargs = client.messages.stream.call_args.kwargs
        self.assertEqual('claude-opus-4-6', kwargs['model'])
        self.assertEqual(32000, kwargs['max_tokens'])
        self.assertNotIn('Kwark', kwargs['system'])
        client.models.list.assert_not_called()

    def test_custom_args_passed_through(self):
        path = self.make_file('doc.txt', 'x')
        _, anthropic_class, client = self.run_transcribe(
            path, model='claude-x', api_key='sk-test', prompt='Do it',
            max_tokens=500)
        anthropic_class.assert_called_once_with(api_key='sk-test')
        kwargs = client.messages.stream.call_args.kwargs
        self.assertEqual('claude-x', kwargs['model'])
        self.assertEqual(500, kwargs['max_tokens'])
        self.assertEqual({'type': 'text', 'text': 'Do it'},
                         self.sent_content(client)[1])

    def test_api_status_error_wrapped(self):
        path = self.make_file('doc.txt', 'x')
        request = httpx.Request('POST', 'https://api.anthropic.com')
        response = httpx.Response(529, request=request)
        error = anthropic.APIStatusError(
            'Overloaded', response=response, body=None)
        anthropic_class, _ = mock_client(error=error)
        with patch(ANTHROPIC, anthropic_class):
            with self.assertRaises(APIError) as ctx:
                transcribe(path)
        self.assertIsInstance(ctx.exception, KwarkAIError)
        self.assertIs(error, ctx.exception.__cause__)
        self.assertIn('Overloaded', str(ctx.exception))

    def test_api_connection_error_wrapped(self):
        path = self.make_file('doc.pdf', b'%PDF')
        request = httpx.Request('POST', 'https://api.anthropic.com')
        error = anthropic.APIConnectionError(request=request)
        anthropic_class, _ = mock_client(error=error)
        with patch(ANTHROPIC, anthropic_class):
            with self.assertRaises(APIError) as ctx:
                transcribe(path)
        self.assertIs(error, ctx.exception.__cause__)

    def test_missing_api_key_wrapped(self):
        path = self.make_file('doc.txt', 'x')
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(APIError) as ctx:
                transcribe(path)
        self.assertIn('ANTHROPIC_API_KEY', str(ctx.exception))

    def test_missing_file(self):
        anthropic_class, _ = mock_client()
        with patch(ANTHROPIC, anthropic_class):
            with self.assertRaises(KwarkAIError) as ctx:
                transcribe(self.dir / 'missing.pdf')
        self.assertIsInstance(ctx.exception.__cause__, OSError)
        anthropic_class.assert_not_called()

    def test_undecodable_text(self):
        path = self.make_file('bad.txt', b'\xff\xfe\xfa')
        anthropic_class, _ = mock_client()
        with patch(ANTHROPIC, anthropic_class):
            with self.assertRaises(KwarkAIError) as ctx:
                transcribe(path)
        self.assertIsInstance(ctx.exception.__cause__, UnicodeDecodeError)

    def test_constants(self):
        self.assertTrue(TRANSCRIBE_PROMPT.startswith(
            'Transcribe the contents of the file to Markdown, verbatim.'))
        self.assertTrue(TRANSCRIBE_PROMPT.endswith(
            'may consist exclusively of description.'))
        self.assertTrue(TRANSCRIBE_DISCLAIMER.startswith(
            'Generated by an AI process from a binary file.'))
        self.assertTrue(TRANSCRIBE_DISCLAIMER.endswith(
            'converted to YAML for machine readability.'))


class TestImportIsolation(TestCase):

    def test_import_kwark_ai_is_lightweight(self):
        code = (
            "import sys, kwark.ai\n"
            "bad = [m for m in sys.modules if m == 'wizlib' "
            "or m.startswith('wizlib.') or m == 'mcp' "
            "or m.startswith('mcp.') or m.startswith('kwark.command') "
            "or m.startswith('kwark.ai_services') or m == 'kwark.app']\n"
            "print(','.join(bad))\n")
        result = subprocess.run(
            [sys.executable, '-c', code], cwd=PROJECT_ROOT,
            capture_output=True, text=True, check=True)
        self.assertEqual('', result.stdout.strip())

    def test_kwark_app_still_available(self):
        import kwark
        from kwark.app import KwarkApp
        self.assertIs(KwarkApp, kwark.KwarkApp)
        with self.assertRaises(AttributeError):
            kwark.NoSuchThing
