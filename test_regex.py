import re

text = """1. 20th July, 2020.\u2014S. 2 [Except clauses (4), (13), (14), (16), (40)], s. 3 to 9 (both inclusive), s. 28 to 73 (both inclusive) [Except
sub-clause (iv) of clause (a) of sub-section (1) of section 58], s. 74 to 81 (both inclusive), s. 82 to 87 (both inclusive), s. 90 and
91 [Except sections 88, 89, 92 and 93], s. 95, 98,100 and 101 [Except clauses (f) to (m) and clauses (zg), (zh) and (zi) of
sub-section 2], s. 102, 103, 105, 106, 107 [Except sections 94, 96, 97, 99, 104], vide Notifn. No. S.O. 2351(E),
dated 15th July, 2020, see Gazette of India, Extraordinary, Part II, sec. 3(ii)."""

DATE_NOTIFICATION = re.compile(
    r"^\s*\d{1,2}(?:st|nd|rd|th)\s+\w+,\s+\d{4}\.\s*[—-].*?(?=^\s*\d{1,2}(?:st|nd|rd|th)\s+\w+,\s+\d{4}\.\s*[—-]|\n\s*\(\d+\)|\n\s*\d+\.\s|\Z)",
    re.MULTILINE | re.DOTALL
)
print('Match:', bool(DATE_NOTIFICATION.search(text)))

# Try simpler pattern
SIMPLE = re.compile(r"^\s*\d+\.\s+\d{1,2}(?:st|nd|rd|th)\s+\w+,\s+\d{4}\.\s*.*?(?=\n\s*\(\d+\)|\n\s*\d+\.\s|\Z)", re.MULTILINE | re.DOTALL)
print('Simple match:', bool(SIMPLE.search(text)))
print('Simple sub:', repr(SIMPLE.sub('', text)))