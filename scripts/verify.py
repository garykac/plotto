import os.path
import re
import subprocess
import sys

def error(msg):
	print 'Error: %s' % (msg)
	sys.exit(1)

class Parser():
	"""Verify script for Plotto"""

	def __init__(self):
		self.in_conflict = False
		self.id = 0

	def validate_link(self, link):
		# Only match S in certain contexts since it is often a mistake for 3 or 8.
		char = ('('
				# Must be first to avoid partial matches: e.g., B + R-B
				'BR-A|BR-B|'
				'A(X|-[1-9])?|'
				'B(X|-[2-58])?|'
				'(D|F|GF|M|NW|P|SR|U)-A|'
				'(D|F|GF|M|SM|SN|SR)-B|'
				'CH|CN|D|FA|GCH|NW|SN|SR|U|'
				'".*?"'
				')')

		# Sequence: (123; 234)
		if ';' in link:
			links = link.split(';')
			for l in links:
				l = l.strip()
				if not self.validate_link(l):
					return False
			return True

		# Alternation: (123 or 234)
		if ' or ' in link:
			links = link.split(' or ')
			for l in links:
				l = l.strip()
				if not self.validate_link(l):
					return False
			return True

		# (a), (b), (c), ...
		# This should only be allowed as the first link in the list.
		if re.match(r'^[a-h]$', link):
			return True
		# ()
		if re.match(r'^$', link):
			return True

		# (123a, b, c)
		m = re.match(r'^\d+([a-h](, [a-h])*)?(?P<extra>.*)$', link)
		if not m:
			return False
		link = m.group('extra')

		# -1-2-3
		m = re.match(r'^(-1)?(-2)?(-3)?(-4)?(?P<extra>.*)$', link)
		if not m:
			return False
		link = m.group('extra')

		# -*, -**, *-**
		m = re.match(r'^( -\*\*?\*?\*?| \*-\*\*)?(?P<extra>.*)$', link)
		if not m:
			return False
		link = m.group('extra')

		# transpose & change
		m = re.match(r'^( tr %s & %s, ch %s to %s)?(?P<extra>.*)$' % (char, char, char, char), link)
		if not m:
			return False
		link = m.group('extra')

		# transpose
		m = re.match(r'^( tr %s & %s)?(?P<extra>.*)$' % (char, char), link)
		if not m:
			return False
		link = m.group('extra')

		# change & add
		m = re.match(r'^( ch %s to %s(, %s to %s)* & add %s)?(?P<extra>.*)$' % (char, char, char, char, char), link)
		if not m:
			return False
		link = m.group('extra')

		# change: A to B & X and Y to Z
		m = re.match(r'^( ch %s to %s & %s and %s to %s)?(?P<extra>.*)$' % (char, char, char, char, char), link)
		if not m:
			return False
		link = m.group('extra')

		# change
		m = re.match(r'^( ch %s to %s((, %s to %s)* & %s to %s)?)?(?P<extra>.*)$' % (char, char, char, char, char, char), link)
		if not m:
			return False
		link = m.group('extra')

		# add
		m = re.match(r'^( add %s)?(?P<extra>.*)$' % (char), link)
		if not m:
			return False
		link = m.group('extra')

		return len(link) == 0

	# Process an entire line from the file.
	def process_line(self, line):
		# Conflicts end on page 190.
		m = re.match(r'^-- page 190$', line)
		if m:
			self.in_conflict = False
			return

		# Ignore comments.
		m = re.match(r'^--', line)
		if m:
			return

		# Start of new B-clause section ends the current Conflict.
		m = re.match(r'^B{\d+}', line)
		if m:
			self.is_conflict = False
			return

		m = re.match(r'^Conflict{(\d+)}$', line)
		if m:
			self.in_conflict = True
			self.first_lead_up = True
			self.next_is_lead_up = False
			self.id = int(m.group(1))
			return

		line = line.strip();

		# A blank line in a Conflict means that a new (or the first)
		# option will start on the next line.
		# Reset the lead-up check so we validate each option.
		if len(line) == 0:
			self.next_is_lead_up = True
			return

		if self.in_conflict and self.next_is_lead_up:
			# Make sure all 'lead-up' links are properly formatted.
			if not self.first_lead_up:
				# 2nd, 3rd, ... in a Conflict must begin with (b), (c), ...
				m = re.match(r'^\([a-z]\)', line)
				if not m:
					print line
					error('%s: unexpected prefix' % self.id)

			while len(line) != 0:
				# Q&D regex to catch obviously incorrect chars.
				m = re.match(r'^\(([a-zA-Z\d "&\*,;-]*)\)\s*(.*)$', line)
				if m:
					line = m.group(2)
					if not self.validate_link(m.group(1)):
						error('%s: found, but unable to parse: %s' % (self.id, m.group(1)))
				else:
					print line
					error('%s: not found' % self.id)
				self.next_is_lead_up = False
				self.first_lead_up = False

	def process(self, src):
		if not os.path.isfile(src):
			error('File "%s" doesn\'t exist' % src)

		try:
			infile = open(src, 'r')
		except IOError as e:
			error('Unable to open "%s" for reading: %s' % (src, e))

		for line in infile:
			self.process_line(line)

		infile.close()


def main():
	infilename = '../plotto.txt'

	parser = Parser()
	parser.process(infilename)

if __name__ == '__main__':
	main()
