import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from wizlib.test_case import WizLibTestCase

from kwark import KwarkApp
from kwark.command import KwarkCommand


class TestCommandHelp(WizLibTestCase):
    """Every command's --help works through KwarkApp.start, as the CLI runs
    it, and missing required arguments give a clear error (issue #24)"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.config = os.path.join(self._tmp.name, 'kwark.yml')
        with open(self.config, 'w') as f:
            f.write('kwark: {}\n')

    def tearDown(self):
        self._tmp.cleanup()

    def _start(self, *args, text=''):
        """Run through KwarkApp.start; return the exit code (None if it
        didn't exit), stdout and stderr"""
        code = None
        with \
                patch.dict(os.environ, {'KWARK_CONFIG': self.config}), \
                patch('sys.stdin.isatty', return_value=True), \
                self.patch_stream(text), \
                self.patchout() as out, \
                self.patcherr() as err:
            try:
                KwarkApp.start(*args)
            except SystemExit as exit:
                code = exit.code
        return code, out.getvalue(), err.getvalue()

    def _names(self):
        KwarkApp.initialize()
        return [c.name for c in KwarkCommand.family_members('name')]

    def test_all_commands_present(self):
        names = self._names()
        for name in ['transcribe', 'extract', 'chat', 'journal']:
            self.assertIn(name, names)

    def test_help_for_every_command(self):
        for name in self._names():
            for option in ['--help', '-h']:
                with self.subTest(command=name, option=option):
                    code, out, err = self._start(name, option)
                    self.assertIsNone(code)
                    self.assertIn(f"usage: kwark {name}", out)
                    self.assertNotIn('unrecognized arguments', out + err)
                    self.assertEqual('', err)

    def test_transcribe_help_shows_arguments(self):
        _, out, _ = self._start('transcribe', '--help')
        self.assertIn('file', out)
        self.assertIn('--no-disclaimer', out)

    def test_extract_help_shows_arguments(self):
        _, out, _ = self._start('extract', '--help')
        self.assertIn('--schema', out)
        self.assertIn('--instructions', out)

    def test_transcribe_missing_file(self):
        m = Mock()
        with patch('kwark.ai.transcribe', m):
            code, out, err = self._start('transcribe')
        self.assertEqual(1, code)
        self.assertIn('A file to transcribe is required', err)
        self.assertNotIn('unrecognized arguments', err)
        self.assertEqual('', out)
        m.assert_not_called()

    def test_extract_missing_schema(self):
        m = Mock()
        with patch('kwark.ai.extract', m):
            code, out, err = self._start('extract', text='Some text')
        self.assertEqual(1, code)
        self.assertIn('--schema/-S is required', err)
        self.assertNotIn('unrecognized arguments', err)
        self.assertEqual('', out)
        m.assert_not_called()


if __name__ == '__main__':
    unittest.main()
