import os
import subprocess
from datetime import date

from wizlib.command import CommandCancellation
from wizlib.ui import Choice, Chooser, Emphasis

from kwark.command import AICommand
from kwark.util import load_prompt


def _prev_month(d):
    """Return the first day of the month before d."""
    if d.month == 1:
        return d.replace(year=d.year - 1, month=12, day=1)
    return d.replace(month=d.month - 1, day=1)


def _next_month(d):
    """Return the first day of the month after d."""
    if d.month == 12:
        return d.replace(year=d.year + 1, month=1, day=1)
    return d.replace(month=d.month + 1, day=1)


class JournalCommand(AICommand):
    """Personal journal command. Records journal entries and
    provides AI-powered insights."""

    name = 'journal'

    def handle_vals(self):
        super().handle_vals()
        journal_dir = self.app.config.get('kwark-journal-dir')
        if not journal_dir:
            raise CommandCancellation(
                "Error: journal-dir is not configured"
            )
        self.journal_dir = os.path.expanduser(journal_dir)
        self.editor = self.app.config.get('kwark-editor')

    def _today(self):
        """Return today's date. Isolated for testability."""
        return date.today()

    @AICommand.wrap
    def execute(self):
        today = self._today()
        this_month = today.replace(day=1)
        previous_month = _prev_month(this_month)
        start_of_previous_year = date(this_month.year - 1, 1, 1)

        summary_file = self._summary_path(previous_month)
        if not os.path.exists(summary_file):
            self._create_summary(
                start_of_previous_year,
                previous_month,
                summary_file,
            )

        while True:
            entry = self._edit_entry(today)
            if entry and entry.strip():
                prior_this_month = self._read_file(
                    self._journal_path(this_month)
                )
                self._append_entry(today, this_month, entry)
                feedback = self._provide_feedback(
                    summary_file, prior_this_month, entry
                )
                print(entry + '\n\n' + feedback, end='')
            print('\n\n', end='')
            chooser = Chooser('Add another entry?', 'continue', [
                Choice('continue', 'cC'),
                Choice('stop', 'sS'),
            ])
            choice = self.app.ui.get_option(chooser)
            if choice == 'stop':
                break

    def _read_file(self, path):
        """Return file contents or empty string if file does not exist."""
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
        return ''

    def _append_entry(self, today, this_month, entry):
        """Append the entry to the monthly journal file, creating it if
        needed. Each date gets a heading; multiple entries on the same
        day are separated by a horizontal rule."""
        journal_path = self._journal_path(this_month)
        os.makedirs(os.path.dirname(journal_path), exist_ok=True)
        heading = today.strftime('# %Y-%m-%d')
        if os.path.exists(journal_path):
            with open(journal_path) as f:
                existing = f.read()
            if heading in existing:
                addition = '\n\n---\n\n' + entry
            else:
                addition = '\n\n' + heading + '\n\n' + entry
            with open(journal_path, 'a') as f:
                f.write(addition)
        else:
            with open(journal_path, 'w') as f:
                f.write(heading + '\n\n' + entry)

    def _provide_feedback(self, summary_file, this_month_text, entry):
        """Query AI for feedback/analysis of the new journal entry."""
        guidelines_path = os.path.join(
            self.journal_dir, 'feedback-prompt.md'
        )
        if not os.path.exists(guidelines_path):
            self.app.ui.send(
                "Note: no feedback-prompt.md found in journal directory.",
                emphasis=Emphasis.GENERAL,
            )
        guidelines = self._read_file(guidelines_path)
        summary = self._read_file(summary_file)
        prompt = load_prompt('journal-feedback').format(
            guidelines=guidelines,
            summary=summary,
            this_month=this_month_text,
            entry=entry,
        )
        self.app.ui.send(
            "Thinking about feedback...",
            emphasis=Emphasis.GENERAL,
        )
        return self.ai_service.ask(prompt)

    def _journal_path(self, month):
        """Return the path for the monthly journal file."""
        return os.path.join(
            self.journal_dir,
            month.strftime('%Y'),
            month.strftime('%Y%m') + '-journal.md',
        )

    def _summary_path(self, month):
        """Return the path for the monthly summary file."""
        return os.path.join(
            self.journal_dir,
            month.strftime('%Y'),
            month.strftime('%Y%m') + '-summary.md',
        )

    def _entry_path(self, today):
        """Return the path for the temporary entry file."""
        return os.path.join(
            self.journal_dir,
            today.strftime('%Y'),
            today.strftime('%Y%m%d') + '-temp.md',
        )

    def _edit_entry(self, today):
        """Open a dated entry file in the configured editor and
        return the content the user typed."""
        entry_path = self._entry_path(today)
        os.makedirs(os.path.dirname(entry_path), exist_ok=True)
        try:
            open(entry_path, 'w').close()
            subprocess.run(
                self.editor.split() + [entry_path], check=True
            )
            with open(entry_path) as f:
                return f.read()
        finally:
            if os.path.exists(entry_path):
                os.unlink(entry_path)

    def _create_summary(self, start, end, summary_file):
        """Concatenate journal files from start through end,
        query AI for a summary, and write the summary file."""
        texts = []
        month = start.replace(day=1)
        while month <= end:
            path = self._journal_path(month)
            if os.path.exists(path):
                with open(path) as f:
                    texts.append(f.read())
            month = _next_month(month)

        combined = '\n\n'.join(texts)
        prompt = load_prompt('journal-summary').format(text=combined)
        range_label = (
            f"{start.strftime('%Y%m')} through {end.strftime('%Y%m')}"
        )
        self.app.ui.send(
            f"Building summary for {range_label}...",
            emphasis=Emphasis.GENERAL,
        )
        summary = self.ai_service.ask(prompt)
        title = f"# Journal summary: {range_label}\n\n"

        os.makedirs(os.path.dirname(summary_file), exist_ok=True)
        with open(summary_file, 'w') as f:
            f.write(title + summary)
