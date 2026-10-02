import os
import tempfile
import unittest
from datetime import date
from unittest.mock import Mock, patch

from wizlib.test_case import WizLibTestCase
from wizlib.config_handler import ConfigHandler

from kwark import KwarkApp
from test import patch_ai_service

TODAY_TARGET = (
    'kwark.command.journal_command.JournalCommand._today'
)
SUBPROC_TARGET = 'subprocess.run'


def noop_editor(cmd, check):
    """Simulate editor that writes nothing."""
    pass


class TestJournalCommand(WizLibTestCase):

    def _make_app(self, journal_dir, editor='/bin/vi'):
        with patch('sys.stdin.isatty', return_value=True):
            app = KwarkApp()
            app.config = ConfigHandler.fake(
                kwark_api_anthropic_key='k',
                kwark_journal_dir=journal_dir,
                kwark_editor=editor,
            )
        return app

    def test_summary_created_when_missing(self):
        """Summary file is created via AI when it does not exist."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            summary_path = os.path.join(
                d, '2026', '202603-summary.md'
            )
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            with open(
                os.path.join(month_dir, '202603-journal.md'), 'w'
            ) as f:
                f.write('March notes')

            m = Mock()
            mi = Mock()
            mi.ask.return_value = 'AI summary'
            m.return_value = mi

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr() as err, \
                    patch_ai_service(m), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=noop_editor), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')

            self.assertTrue(os.path.exists(summary_path))
            with open(summary_path) as f:
                content = f.read()
            self.assertIn(
                '# Journal summary: 202501 through 202603', content
            )
            self.assertIn('AI summary', content)
            err.seek(0)
            self.assertIn('202501 through 202603', err.read())

    def test_summary_not_recreated_when_present(self):
        """Summary file is not recreated if it already exists."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            summary_path = os.path.join(
                month_dir, '202603-summary.md'
            )
            with open(summary_path, 'w') as f:
                f.write('existing summary')

            m = Mock()
            mi = Mock()
            m.return_value = mi

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(m), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=noop_editor), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')

            mi.ask.assert_not_called()
            with open(summary_path) as f:
                self.assertEqual('existing summary', f.read())

    def test_journal_files_concatenated_for_summary(self):
        """All journal files from start_of_previous_year through
        previous_month are concatenated before sending to AI."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)

            for yyyy, mm, text in [
                ('2025', '01', 'Jan 25'),
                ('2025', '06', 'Jun 25'),
                ('2026', '01', 'Jan 26'),
                ('2026', '02', 'Feb 26'),
                ('2026', '03', 'Mar 26'),
            ]:
                p = os.path.join(d, yyyy)
                os.makedirs(p, exist_ok=True)
                with open(
                    os.path.join(p, f'{yyyy}{mm}-journal.md'), 'w'
                ) as f:
                    f.write(text)

            m = Mock()
            mi = Mock()
            mi.ask.return_value = 'summary'
            m.return_value = mi

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(m), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=noop_editor), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')

            prompt_arg = mi.ask.call_args[0][0]
            self.assertIn('Jan 25', prompt_arg)
            self.assertIn('Jun 25', prompt_arg)
            self.assertIn('Jan 26', prompt_arg)
            self.assertIn('Feb 26', prompt_arg)
            self.assertIn('Mar 26', prompt_arg)

    def test_summary_spans_year_boundary(self):
        """When today is in January, previous_month is December of
        last year and start_of_previous_year is Jan of the year
        before that."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 1, 15)
            m_dir = os.path.join(d, '2025')
            os.makedirs(m_dir)
            with open(
                os.path.join(m_dir, '202512-journal.md'), 'w'
            ) as f:
                f.write('Dec 25')

            m = Mock()
            mi = Mock()
            mi.ask.return_value = 'year summary'
            m.return_value = mi

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(m), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=noop_editor), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')

            summary_path = os.path.join(
                d, '2025', '202512-summary.md'
            )
            self.assertTrue(os.path.exists(summary_path))

    def test_missing_journal_dir_config(self):
        """Command prints error when journal-dir is not configured."""
        with patch('sys.stdin.isatty', return_value=True):
            app = KwarkApp()
            app.config = ConfigHandler.fake(
                kwark_api_anthropic_key='k'
            )

        with \
                self.patch_stream(''), \
                self.patchout(), \
                self.patcherr() as err, \
                patch_ai_service():
            app.parse_run('journal')

        err.seek(0)
        self.assertIn('journal-dir', err.read())

    def test_missing_journal_files_no_error(self):
        """Command does not fail when no journal files exist yet."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)

            m = Mock()
            mi = Mock()
            mi.ask.return_value = 'empty summary'
            m.return_value = mi

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(m), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=noop_editor), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')


    def test_temp_file_contains_date_header(self):
        """Entry file is created empty."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            with open(
                os.path.join(month_dir, '202603-summary.md'), 'w'
            ) as f:
                f.write('s')

            contents = []

            def fake_run(cmd, check):
                with open(cmd[1]) as f:
                    contents.append(f.read())

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=fake_run), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')

            self.assertEqual('', contents[0])

    def test_editor_opens_temp_file_and_output_is_dumped(self):
        """Editor is opened with a temp file; content is printed to output."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            summary_path = os.path.join(
                month_dir, '202603-summary.md'
            )
            with open(summary_path, 'w') as f:
                f.write('existing summary')

            def fake_run(cmd, check):
                with open(cmd[1], 'w') as f:
                    f.write('my journal entry')

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout() as out, \
                    self.patcherr(), \
                    patch_ai_service(), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch('subprocess.run', side_effect=fake_run), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')

            out.seek(0)
            self.assertIn('my journal entry', out.read())

    def test_editor_uses_configured_editor(self):
        """subprocess.run is called with the configured editor."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            with open(
                os.path.join(month_dir, '202603-summary.md'), 'w'
            ) as f:
                f.write('s')

            captured = []

            def fake_run(cmd, check):
                captured.append(cmd)
                with open(cmd[1], 'w') as f:
                    f.write('x')

            app = self._make_app(d, editor='/usr/bin/nano')
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch('subprocess.run', side_effect=fake_run), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')

            self.assertEqual('/usr/bin/nano', captured[0][0])
            self.assertTrue(
                captured[0][1].endswith('20260426-temp.md')
            )


    def test_ai_feedback_queried_when_entry_not_empty(self):
        """AI is queried for feedback when user enters journal content."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            with open(
                os.path.join(month_dir, '202603-summary.md'), 'w'
            ) as f:
                f.write('prior summary')
            with open(
                os.path.join(month_dir, '202604-journal.md'), 'w'
            ) as f:
                f.write('earlier this month')
            with open(
                os.path.join(d, 'feedback-prompt.md'), 'w'
            ) as f:
                f.write('be kind')

            def fake_run(cmd, check):
                with open(cmd[1], 'w') as f:
                    f.write('today I did something')

            m = Mock()
            mi = Mock()
            mi.ask.return_value = 'AI wisdom'
            m.return_value = mi

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout() as out, \
                    self.patcherr() as err, \
                    patch_ai_service(m), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=fake_run), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')

            # AI queried once for feedback
            self.assertEqual(1, mi.ask.call_count)
            prompt_arg = mi.ask.call_args[0][0]
            self.assertIn('be kind', prompt_arg)
            self.assertIn('prior summary', prompt_arg)
            self.assertIn('earlier this month', prompt_arg)
            self.assertIn('today I did something', prompt_arg)
            out.seek(0)
            self.assertIn('AI wisdom', out.read())
            err.seek(0)
            self.assertIn('Thinking about feedback', err.read())

    def test_missing_feedback_prompt_noted_in_stderr(self):
        """A warning is printed to stderr when feedback-prompt.md is absent."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            with open(
                os.path.join(month_dir, '202603-summary.md'), 'w'
            ) as f:
                f.write('s')

            def fake_run(cmd, check):
                with open(cmd[1], 'w') as f:
                    f.write('an entry')

            m = Mock()
            mi = Mock()
            mi.ask.return_value = 'AI feedback'
            m.return_value = mi

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr() as err, \
                    patch_ai_service(m), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=fake_run), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')

            err.seek(0)
            self.assertIn('feedback-prompt.md', err.read())

    def test_ai_feedback_not_queried_when_entry_empty(self):
        """AI is not queried for feedback when user saves empty entry."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            with open(
                os.path.join(month_dir, '202603-summary.md'), 'w'
            ) as f:
                f.write('s')

            m = Mock()
            mi = Mock()
            m.return_value = mi

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(m), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=noop_editor), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')

            mi.ask.assert_not_called()

    def test_entry_appended_to_new_journal_file(self):
        """Entry creates the monthly journal file when it does not exist."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            with open(
                os.path.join(month_dir, '202603-summary.md'), 'w'
            ) as f:
                f.write('s')

            def fake_run(cmd, check):
                with open(cmd[1], 'w') as f:
                    f.write('first entry')

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=fake_run), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')

            journal_path = os.path.join(
                month_dir, '202604-journal.md'
            )
            self.assertTrue(os.path.exists(journal_path))
            with open(journal_path) as f:
                content = f.read()
            self.assertIn('# 2026-04-26', content)
            self.assertIn('first entry', content)

    def test_entry_appended_to_existing_journal_new_date(self):
        """Entry is appended with a new date heading when no entry
        for today exists yet."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            with open(
                os.path.join(month_dir, '202603-summary.md'), 'w'
            ) as f:
                f.write('s')
            with open(
                os.path.join(month_dir, '202604-journal.md'), 'w'
            ) as f:
                f.write('# 2026-04-10\n\nold entry')

            def fake_run(cmd, check):
                with open(cmd[1], 'w') as f:
                    f.write('new entry today')

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=fake_run), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')

            journal_path = os.path.join(
                month_dir, '202604-journal.md'
            )
            with open(journal_path) as f:
                content = f.read()
            self.assertIn('# 2026-04-10', content)
            self.assertIn('old entry', content)
            self.assertIn('# 2026-04-26', content)
            self.assertIn('new entry today', content)

    def test_second_entry_same_day_separated_by_hr(self):
        """A second entry for the same day is separated by a horizontal
        rule."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            with open(
                os.path.join(month_dir, '202603-summary.md'), 'w'
            ) as f:
                f.write('s')
            with open(
                os.path.join(month_dir, '202604-journal.md'), 'w'
            ) as f:
                f.write('# 2026-04-26\n\nmorning entry')

            def fake_run(cmd, check):
                with open(cmd[1], 'w') as f:
                    f.write('evening entry')

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=fake_run), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')

            journal_path = os.path.join(
                month_dir, '202604-journal.md'
            )
            with open(journal_path) as f:
                content = f.read()
            self.assertIn('morning entry', content)
            self.assertIn('---', content)
            self.assertIn('evening entry', content)
            # Heading should appear only once
            self.assertEqual(1, content.count('# 2026-04-26'))

    def test_empty_entry_not_appended_to_journal(self):
        """An empty entry does not modify the monthly journal file."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            with open(
                os.path.join(month_dir, '202603-summary.md'), 'w'
            ) as f:
                f.write('s')

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=noop_editor), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')

            journal_path = os.path.join(
                month_dir, '202604-journal.md'
            )
            self.assertFalse(os.path.exists(journal_path))

    def test_this_month_prior_content_used_for_feedback(self):
        """Feedback prompt uses the journal content from before the new
        entry was appended, so the new entry appears only under 'New
        entry' and not duplicated in 'This month's entries'."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            with open(
                os.path.join(month_dir, '202603-summary.md'), 'w'
            ) as f:
                f.write('s')
            with open(
                os.path.join(month_dir, '202604-journal.md'), 'w'
            ) as f:
                f.write('# 2026-04-10\n\nprior content')

            def fake_run(cmd, check):
                with open(cmd[1], 'w') as f:
                    f.write('brand new entry')

            m = Mock()
            mi = Mock()
            mi.ask.return_value = 'feedback'
            m.return_value = mi

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(m), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=fake_run), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')

            prompt_arg = mi.ask.call_args[0][0]
            # prior content in this_month section
            self.assertIn('prior content', prompt_arg)
            # new entry in entry section
            self.assertIn('brand new entry', prompt_arg)
            # new entry should appear only once in the prompt
            self.assertEqual(1, prompt_arg.count('brand new entry'))


    def test_continue_loops_back_to_editor(self):
        """Pressing continue runs the editor a second time."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            with open(
                os.path.join(month_dir, '202603-summary.md'), 'w'
            ) as f:
                f.write('s')

            call_count = [0]

            def fake_run(cmd, check):
                call_count[0] += 1
                with open(cmd[1], 'w') as f:
                    f.write(f'entry {call_count[0]}')

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=fake_run), \
                    self.patch_ttyin('cs'):
                app.parse_run('journal')

            self.assertEqual(2, call_count[0])

    def test_stop_exits_after_one_iteration(self):
        """Pressing stop exits the loop after one editor session."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            with open(
                os.path.join(month_dir, '202603-summary.md'), 'w'
            ) as f:
                f.write('s')

            call_count = [0]

            def fake_run(cmd, check):
                call_count[0] += 1
                with open(cmd[1], 'w') as f:
                    f.write('one entry')

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=fake_run), \
                    self.patch_ttyin('s'):
                app.parse_run('journal')

            self.assertEqual(1, call_count[0])

    def test_default_choice_is_continue(self):
        """Pressing Enter (default) loops back to the editor."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            with open(
                os.path.join(month_dir, '202603-summary.md'), 'w'
            ) as f:
                f.write('s')

            call_count = [0]

            def fake_run(cmd, check):
                call_count[0] += 1
                with open(cmd[1], 'w') as f:
                    f.write(f'entry {call_count[0]}')

            app = self._make_app(d)
            # '\n' selects default (continue), then 's' stops
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=fake_run), \
                    self.patch_ttyin('\ns'):
                app.parse_run('journal')

            self.assertEqual(2, call_count[0])

    def test_second_loop_entry_appended_with_hr(self):
        """A second entry added in the continue loop is appended with
        a horizontal rule when it falls on the same day."""
        with tempfile.TemporaryDirectory() as d:
            today = date(2026, 4, 26)
            month_dir = os.path.join(d, '2026')
            os.makedirs(month_dir)
            with open(
                os.path.join(month_dir, '202603-summary.md'), 'w'
            ) as f:
                f.write('s')

            call_count = [0]

            def fake_run(cmd, check):
                call_count[0] += 1
                with open(cmd[1], 'w') as f:
                    f.write(f'loop entry {call_count[0]}')

            app = self._make_app(d)
            with \
                    self.patch_stream(''), \
                    self.patchout(), \
                    self.patcherr(), \
                    patch_ai_service(), \
                    patch(TODAY_TARGET, return_value=today), \
                    patch(SUBPROC_TARGET, side_effect=fake_run), \
                    self.patch_ttyin('cs'):
                app.parse_run('journal')

            journal_path = os.path.join(month_dir, '202604-journal.md')
            with open(journal_path) as f:
                content = f.read()
            self.assertIn('loop entry 1', content)
            self.assertIn('loop entry 2', content)
            self.assertIn('---', content)
            self.assertEqual(1, content.count('# 2026-04-26'))


if __name__ == '__main__':
    unittest.main()
