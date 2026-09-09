"""Static contracts for the self-contained editorial decoy."""
from html.parser import HTMLParser
from pathlib import Path
import unittest


PAGE = Path(__file__).resolve().parents[1] / 'src/decoy.html'


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class DecoyTests(unittest.TestCase):
    def setUp(self):
        self.source = PAGE.read_text()
        self.page = PageParser()
        self.page.feed(self.source)

    def test_self_contained_and_navigation_targets_exist(self):
        ids = [a['id'] for _, a in self.page.elements if 'id' in a]
        self.assertEqual(len(ids), len(set(ids)))
        for tag, attrs in self.page.elements:
            self.assertNotIn('src', attrs, 'No external assets required')
            if 'href' in attrs:
                self.assertTrue(attrs['href'].startswith('#'))
                self.assertIn(attrs['href'][1:], ids)
            if 'data-read' in attrs:
                self.assertIn(attrs['data-read'], ids)
        for term in ('fetch(', 'XMLHttpRequest', 'localStorage', 'document.cookie'):
            self.assertNotIn(term, self.source)

    def test_readable_without_script_and_accessible_reader(self):
        stories = [a for tag, a in self.page.elements
                   if tag == 'details' and 'story' in a.get('class', '').split()]
        self.assertEqual(len(stories), 6)
        for topic in ('design', 'attention', 'technology'):
            self.assertEqual(sum(s['data-topic'] == topic for s in stories), 2)
        dialogs = [a for tag, a in self.page.elements if tag == 'dialog']
        self.assertEqual(dialogs[0]['aria-labelledby'], 'reader-title')
        self.assertIn('prefers-reduced-motion:reduce', self.source)
        self.assertIn("reader.addEventListener('close'", self.source)
        self.assertIn('opener.focus', self.source)


if __name__ == '__main__':
    unittest.main()
