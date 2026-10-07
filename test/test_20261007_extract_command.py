import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

import yaml
from wizlib.config_handler import ConfigHandler
from wizlib.test_case import WizLibTestCase

from kwark import KwarkApp
from kwark.ai import KwarkAIError, SchemaValidationError


EXTRACT = 'kwark.ai.extract'

SCHEMA = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'amount': {'type': 'number'},
    },
    'required': ['name'],
}

RESULT = {'name': 'Zoë Acme', 'amount': 12.5, 'tags': ['a', 'b']}


class TestExtractCommand(WizLibTestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.yaml_schema = self._write('schema.yaml', yaml.safe_dump(SCHEMA))
        self.json_schema = self._write('schema.json', json.dumps(SCHEMA))

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name, content):
        path = os.path.join(self.tmp, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def _make_app(self, **config):
        with patch('sys.stdin.isatty', return_value=True):
            app = KwarkApp()
            app.config = ConfigHandler.fake(**config)
        return app

    def _run(self, *args, text='Some input text', result=RESULT, **config):
        """Run the command with a mocked extract; return the mock, stdout
        and stderr"""
        m = Mock(return_value=result)
        with \
                self.patch_stream(text), \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch(EXTRACT, m):
            self._make_app(**config).parse_run('extract', *args)
        return m, out.getvalue(), err.getvalue()

    def _start(self, *args, text='Some input text', extract=None):
        """Run through KwarkApp.start (as the CLI does); return the exit
        code, stdout, stderr and the mock"""
        m = extract or Mock(return_value=RESULT)
        config = self._write('kwark.yml', 'kwark: {}\n')
        with \
                patch.dict(os.environ, {'KWARK_CONFIG': config}), \
                patch('sys.stdin.isatty', return_value=True), \
                self.patch_stream(text), \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch(EXTRACT, m):
            with self.assertRaises(SystemExit) as cm:
                KwarkApp.start('extract', *args)
        return cm.exception.code, out.getvalue(), err.getvalue(), m

    # --- schema files ---

    def test_yaml_schema_passed_through(self):
        m, _, _ = self._run('--schema', self.yaml_schema)
        self.assertEqual(SCHEMA, m.call_args[0][1])

    def test_json_schema_passed_through(self):
        m, _, _ = self._run('-S', self.json_schema)
        self.assertEqual(SCHEMA, m.call_args[0][1])

    # --- inputs ---

    def test_stdin_text_passed_through(self):
        m, _, _ = self._run('-S', self.yaml_schema, text='Invoice from X')
        self.assertEqual('Invoice from X', m.call_args[0][0])

    def test_instructions_passed_through(self):
        m, _, _ = self._run('-S', self.yaml_schema,
                            '--instructions', 'Get the name')
        self.assertEqual('Get the name', m.call_args[1]['instructions'])

    def test_instructions_short_option(self):
        m, _, _ = self._run('-S', self.yaml_schema, '-i', 'Short')
        self.assertEqual('Short', m.call_args[1]['instructions'])

    def test_instructions_default_none(self):
        m, _, _ = self._run('-S', self.yaml_schema)
        self.assertIsNone(m.call_args[1]['instructions'])

    # --- output format ---

    def test_output_is_yaml_matching_result(self):
        _, out, err = self._run('-S', self.yaml_schema)
        self.assertEqual(RESULT, yaml.safe_load(out))
        self.assertEqual('', err)

    def test_output_block_style_key_order_unicode(self):
        _, out, _ = self._run('-S', self.yaml_schema)
        self.assertEqual(
            'name: Zoë Acme\namount: 12.5\ntags:\n- a\n- b\n', out)

    # --- model resolution ---

    def test_model_option(self):
        m, _, _ = self._run('-S', self.yaml_schema, '--model', 'claude-x',
                            kwark_extract_model='from-config')
        self.assertEqual('claude-x', m.call_args[1]['model'])

    def test_model_short_option(self):
        m, _, _ = self._run('-S', self.yaml_schema, '-m', 'claude-y')
        self.assertEqual('claude-y', m.call_args[1]['model'])

    def test_model_from_config(self):
        m, _, _ = self._run('-S', self.yaml_schema,
                            kwark_extract_model='from-config',
                            kwark_model='general')
        self.assertEqual('from-config', m.call_args[1]['model'])

    def test_model_default_ignores_general_kwark_model(self):
        m, _, _ = self._run('-S', self.yaml_schema, kwark_model='general')
        self.assertEqual('claude-haiku-4-5', m.call_args[1]['model'])

    def test_model_default(self):
        m, _, _ = self._run('-S', self.yaml_schema)
        self.assertEqual('claude-haiku-4-5', m.call_args[1]['model'])

    # --- api key ---

    def test_api_key_option(self):
        m, _, _ = self._run('-S', self.yaml_schema, '-k', 'opt-key',
                            kwark_api_anthropic_key='cfg-key')
        self.assertEqual('opt-key', m.call_args[1]['api_key'])

    def test_api_key_none_uses_sdk_default(self):
        m, _, _ = self._run('-S', self.yaml_schema)
        self.assertIsNone(m.call_args[1]['api_key'])

    # --- errors ---

    def test_extract_error_exits_non_zero_with_message_on_stderr(self):
        code, out, err, _ = self._start(
            '-S', self.yaml_schema,
            extract=Mock(side_effect=SchemaValidationError('missing name')))
        self.assertEqual(1, code)
        self.assertIn('missing name', err)
        self.assertEqual('', out)

    def test_error_propagates_from_run(self):
        m = Mock(side_effect=KwarkAIError('boom'))
        with \
                self.patch_stream('text'), \
                self.patchout() as out, \
                self.patcherr(), \
                patch(EXTRACT, m):
            with self.assertRaises(KwarkAIError):
                self._make_app().parse_run('extract', '-S', self.yaml_schema)
        self.assertEqual('', out.getvalue())

    def test_missing_schema_file(self):
        missing = os.path.join(self.tmp, 'nope.yaml')
        code, out, err, m = self._start('-S', missing)
        self.assertEqual(1, code)
        self.assertIn("Can't read schema file", err)
        self.assertIn('nope.yaml', err)
        self.assertEqual('', out)
        m.assert_not_called()

    def test_invalid_schema_file(self):
        bad = self._write('bad.json', '{"type": "object", ')
        code, out, err, m = self._start('-S', bad)
        self.assertEqual(1, code)
        self.assertIn('Invalid YAML/JSON', err)
        self.assertEqual('', out)
        m.assert_not_called()

    def test_schema_not_a_mapping(self):
        bad = self._write('list.yaml', '- a\n- b\n')
        code, out, err, m = self._start('-S', bad)
        self.assertEqual(1, code)
        self.assertIn('must contain a mapping', err)
        self.assertEqual('', out)
        m.assert_not_called()

    def test_empty_stdin(self):
        code, out, err, m = self._start('-S', self.yaml_schema, text='  \n')
        self.assertEqual(1, code)
        self.assertIn('No input text', err)
        self.assertEqual('', out)
        m.assert_not_called()


if __name__ == '__main__':
    unittest.main()
