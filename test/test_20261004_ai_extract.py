"""kwark.ai.extract() returns a dict matching a JSON schema (library layer)"""
import os
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

import anthropic
import httpx

from kwark.ai import APIError
from kwark.ai import KwarkAIError
from kwark.ai import MissingToolUseError
from kwark.ai import SchemaValidationError
from kwark.ai import TruncatedResponseError
from kwark.ai import extract


ANTHROPIC = 'kwark.ai.client.Anthropic'

SCHEMA = {
    'type': 'object',
    'properties': {
        'category': {'type': 'string'},
        'amount': {'type': 'number'},
        'note': {'type': 'string'},
    },
    'required': ['category', 'amount'],
}


def tool_block(data, name='record'):
    return SimpleNamespace(type='tool_use', name=name, id='t1', input=data)


def fake_message(content=None, stop_reason='tool_use'):
    if content is None:
        content = [tool_block({'category': 'invoice', 'amount': 12.5})]
    return SimpleNamespace(content=content, stop_reason=stop_reason)


def mock_client(message=None, error=None):
    """Return a mock Anthropic class whose client returns the message"""
    client = MagicMock()
    client.messages.create.return_value = message or fake_message()
    if error:
        client.messages.create.side_effect = error
    return MagicMock(return_value=client), client


class TestExtract(TestCase):

    def run_extract(self, message=None, schema=SCHEMA, text='Invoice $12.50',
                    **kwargs):
        anthropic_class, client = mock_client(message)
        with patch(ANTHROPIC, anthropic_class):
            result = extract(text, schema, **kwargs)
        return result, anthropic_class, client

    def test_happy_path(self):
        result, _, _ = self.run_extract()
        self.assertEqual({'category': 'invoice', 'amount': 12.5}, result)
        self.assertIsInstance(result, dict)

    def test_forces_tool(self):
        _, _, client = self.run_extract()
        kwargs = client.messages.create.call_args.kwargs
        self.assertEqual(1, len(kwargs['tools']))
        tool = kwargs['tools'][0]
        self.assertIs(SCHEMA, tool['input_schema'])
        self.assertEqual({'type': 'tool', 'name': tool['name']},
                         kwargs['tool_choice'])
        self.assertEqual([{'role': 'user', 'content': 'Invoice $12.50'}],
                         kwargs['messages'])

    def test_defaults_passed_through(self):
        _, anthropic_class, client = self.run_extract()
        anthropic_class.assert_called_once_with(api_key=None)
        kwargs = client.messages.create.call_args.kwargs
        self.assertEqual('claude-sonnet-5', kwargs['model'])
        self.assertNotIn('thinking', kwargs)
        self.assertEqual(4096, kwargs['max_tokens'])
        self.assertNotIn('Kwark', kwargs['system'])
        client.models.list.assert_not_called()

    def test_custom_args_passed_through(self):
        _, anthropic_class, client = self.run_extract(
            instructions='Classify the document.', model='claude-x',
            api_key='sk-test', max_tokens=300)
        anthropic_class.assert_called_once_with(api_key='sk-test')
        kwargs = client.messages.create.call_args.kwargs
        self.assertEqual('claude-x', kwargs['model'])
        self.assertNotIn('thinking', kwargs)
        self.assertEqual(300, kwargs['max_tokens'])
        self.assertIn('Classify the document.', kwargs['system'])

    def test_forced_tool_not_strict(self):
        _, _, client = self.run_extract()
        tool = client.messages.create.call_args.kwargs['tools'][0]
        self.assertNotIn('strict', tool)

    def test_auto_strict_tool_for_models_rejecting_forced_tool_use(self):
        for model in ['claude-opus-5-5', 'claude-sonnet-5-5',
                      'claude-fable-5-1', 'claude-mythos-5-1']:
            with self.subTest(model=model):
                result, _, client = self.run_extract(model=model)
                kwargs = client.messages.create.call_args.kwargs
                self.assertEqual(model, kwargs['model'])
                self.assertEqual({'type': 'auto'}, kwargs['tool_choice'])
                self.assertNotIn('thinking', kwargs)
                self.assertEqual(1, len(kwargs['tools']))
                tool = kwargs['tools'][0]
                self.assertIs(True, tool['strict'])
                self.assertEqual(
                    {'type': 'object',
                     'properties': {'category': {'type': 'string'},
                                    'amount': {'type': 'number'},
                                    'note': {'type': 'string'}},
                     'additionalProperties': False,
                     'required': ['category', 'amount']},
                    tool['input_schema'])
                self.assertNotIn('additionalProperties', SCHEMA)
                self.assertEqual(
                    {'category': 'invoice', 'amount': 12.5}, result)

    def test_auto_strict_tool_not_called(self):
        message = fake_message(
            [SimpleNamespace(type='text', text='No')], stop_reason='end_turn')
        with self.assertRaises(MissingToolUseError):
            self.run_extract(message=message, model='claude-sonnet-5-5')

    def test_auto_strict_tool_missing_required_property(self):
        message = fake_message([tool_block({'category': 'invoice'})])
        with self.assertRaises(SchemaValidationError):
            self.run_extract(message=message, model='claude-opus-5-5')

    def test_schema_not_convertible_for_strict_tool(self):
        for prop in [{}, {'type': ['string', 'null']}, 'x']:
            with self.subTest(prop=prop):
                schema = {'type': 'object', 'properties': {'a': prop}}
                anthropic_class, _ = mock_client()
                with patch(ANTHROPIC, anthropic_class):
                    with self.assertRaises(KwarkAIError) as ctx:
                        extract('text', schema, model='claude-sonnet-5-5')
                self.assertIsNotNone(ctx.exception.__cause__)
                anthropic_class.assert_not_called()

    def test_tool_input_not_a_dict(self):
        for data in ['{"category": "invoice"}', None, ['invoice']]:
            with self.subTest(data=data):
                message = fake_message([tool_block(data)])
                with self.assertRaises(SchemaValidationError):
                    self.run_extract(message=message)

    def test_no_instructions_in_system(self):
        _, _, client = self.run_extract()
        system = client.messages.create.call_args.kwargs['system']
        self.assertNotIn('\n\n', system)

    def test_missing_required_property(self):
        message = fake_message([tool_block({'category': 'invoice'})])
        with self.assertRaises(SchemaValidationError) as ctx:
            self.run_extract(message=message)
        self.assertIsInstance(ctx.exception, KwarkAIError)
        self.assertIn('amount', str(ctx.exception))

    def test_schema_without_required(self):
        schema = {'type': 'object', 'properties': {}}
        message = fake_message([tool_block({})])
        result, _, _ = self.run_extract(message=message, schema=schema)
        self.assertEqual({}, result)

    def test_picks_matching_tool_block(self):
        message = fake_message([
            SimpleNamespace(type='text', text='Here you go'),
            tool_block({'x': 1}, name='other'),
            tool_block({'category': 'receipt', 'amount': 3})])
        result, _, _ = self.run_extract(message=message)
        self.assertEqual({'category': 'receipt', 'amount': 3}, result)

    def test_no_tool_use_block(self):
        message = fake_message(
            [SimpleNamespace(type='text', text='No')], stop_reason='end_turn')
        with self.assertRaises(MissingToolUseError) as ctx:
            self.run_extract(message=message)
        self.assertIsInstance(ctx.exception, KwarkAIError)

    def test_max_tokens_raises(self):
        message = fake_message(stop_reason='max_tokens')
        with self.assertRaises(TruncatedResponseError) as ctx:
            self.run_extract(message=message, max_tokens=10)
        self.assertIn('max_tokens=10', str(ctx.exception))

    def test_invalid_schema(self):
        for schema in [None, {'type': 'array'}, {'properties': {}}]:
            with self.subTest(schema=schema):
                anthropic_class, _ = mock_client()
                with patch(ANTHROPIC, anthropic_class):
                    with self.assertRaises(KwarkAIError):
                        extract('text', schema)
                anthropic_class.assert_not_called()

    def test_api_status_error_wrapped(self):
        request = httpx.Request('POST', 'https://api.anthropic.com')
        response = httpx.Response(529, request=request)
        error = anthropic.APIStatusError(
            'Overloaded', response=response, body=None)
        anthropic_class, _ = mock_client(error=error)
        with patch(ANTHROPIC, anthropic_class):
            with self.assertRaises(APIError) as ctx:
                extract('text', SCHEMA)
        self.assertIsInstance(ctx.exception, KwarkAIError)
        self.assertIs(error, ctx.exception.__cause__)
        self.assertIn('Overloaded', str(ctx.exception))

    def test_api_connection_error_wrapped(self):
        request = httpx.Request('POST', 'https://api.anthropic.com')
        error = anthropic.APIConnectionError(request=request)
        anthropic_class, _ = mock_client(error=error)
        with patch(ANTHROPIC, anthropic_class):
            with self.assertRaises(APIError) as ctx:
                extract('text', SCHEMA)
        self.assertIs(error, ctx.exception.__cause__)

    def test_missing_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(APIError) as ctx:
                extract('text', SCHEMA)
        self.assertIn('ANTHROPIC_API_KEY', str(ctx.exception))
