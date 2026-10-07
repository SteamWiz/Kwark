import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from wizlib.config_handler import ConfigHandler
from wizlib.test_case import WizLibTestCase

from kwark import KwarkApp
from kwark.ai import KwarkAIError, TRANSCRIBE_DISCLAIMER
from kwark.ai import UnsupportedFileTypeError


TRANSCRIBE = 'kwark.ai.transcribe'
HEADER = f"<!-- {TRANSCRIBE_DISCLAIMER} -->\n\n"


class TestTranscribeCommand(WizLibTestCase):

    def _make_app(self, **config):
        with patch('sys.stdin.isatty', return_value=True):
            app = KwarkApp()
            app.config = ConfigHandler.fake(**config)
        return app

    def _run(self, *args, markdown='# Title\n\nBody', **config):
        """Run the command with a mocked transcribe; return the mock, stdout
        and stderr"""
        m = Mock(return_value=markdown)
        with \
                self.patch_stream(''), \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch(TRANSCRIBE, m):
            self._make_app(**config).parse_run('transcribe', *args)
        return m, out.getvalue(), err.getvalue()

    # --- output format ---

    def test_output_has_disclaimer_blank_line_then_markdown(self):
        _, out, err = self._run('x.pdf')
        self.assertEqual(HEADER + '# Title\n\nBody\n', out)
        self.assertEqual('', err)

    def test_trailing_newlines_normalised(self):
        _, out, _ = self._run('x.pdf', markdown='Body\n\n\n')
        self.assertEqual(HEADER + 'Body\n', out)

    def test_no_disclaimer(self):
        _, out, _ = self._run('x.pdf', '--no-disclaimer')
        self.assertEqual('# Title\n\nBody\n', out)

    def test_file_passed_to_transcribe(self):
        m, _, _ = self._run('/tmp/doc.pdf')
        self.assertEqual(('/tmp/doc.pdf',), m.call_args[0])

    # --- model resolution ---

    def test_model_option(self):
        m, _, _ = self._run('x.pdf', '--model', 'claude-test-1',
                            kwark_transcribe_model='from-config')
        self.assertEqual('claude-test-1', m.call_args[1]['model'])

    def test_model_short_option(self):
        m, _, _ = self._run('x.pdf', '-m', 'claude-test-2')
        self.assertEqual('claude-test-2', m.call_args[1]['model'])

    def test_model_from_config(self):
        m, _, _ = self._run('x.pdf', kwark_transcribe_model='from-config',
                            kwark_model='general')
        self.assertEqual('from-config', m.call_args[1]['model'])

    def test_model_default_ignores_general_kwark_model(self):
        m, _, _ = self._run('x.pdf', kwark_model='general')
        self.assertEqual('claude-opus-4-6', m.call_args[1]['model'])

    def test_model_default(self):
        m, _, _ = self._run('x.pdf')
        self.assertEqual('claude-opus-4-6', m.call_args[1]['model'])

    # --- api key ---

    def test_api_key_option(self):
        m, _, _ = self._run('x.pdf', '--api-key', 'opt-key',
                            kwark_api_anthropic_key='cfg-key')
        self.assertEqual('opt-key', m.call_args[1]['api_key'])

    def test_api_key_from_config(self):
        m, _, _ = self._run('x.pdf', kwark_api_anthropic_key='cfg-key')
        self.assertEqual('cfg-key', m.call_args[1]['api_key'])

    def test_api_key_none_uses_sdk_default(self):
        m, _, _ = self._run('x.pdf')
        self.assertIsNone(m.call_args[1]['api_key'])

    # --- errors ---

    def test_error_propagates_from_run(self):
        m = Mock(side_effect=KwarkAIError('boom'))
        with \
                self.patch_stream(''), \
                self.patchout() as out, \
                self.patcherr(), \
                patch(TRANSCRIBE, m):
            with self.assertRaises(KwarkAIError):
                self._make_app().parse_run('transcribe', 'x.pdf')
        self.assertEqual('', out.getvalue())

    def test_error_exits_non_zero_with_message_on_stderr(self):
        m = Mock(side_effect=UnsupportedFileTypeError(
            "Unsupported file type '.doc'"))
        with tempfile.TemporaryDirectory() as tmp:
            config = os.path.join(tmp, 'kwark.yml')
            with open(config, 'w') as f:
                f.write('kwark: {}\n')
            with \
                    patch.dict(os.environ, {'KWARK_CONFIG': config}), \
                    self.patch_stream(''), \
                    self.patchout() as out, \
                    self.patcherr() as err, \
                    patch(TRANSCRIBE, m):
                with self.assertRaises(SystemExit) as cm:
                    KwarkApp.start('transcribe', 'x.doc')
        self.assertEqual(1, cm.exception.code)
        self.assertIn("Unsupported file type '.doc'", err.getvalue())
        self.assertEqual('', out.getvalue())


if __name__ == '__main__':
    unittest.main()
