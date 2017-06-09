#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
		self.in_conflict_section = False
		self.in_conflict = False
		self.id = 0

		self.conflict_text = []
		self.links = {}

	def validate_link(self, link):
		# Only match S in certain contexts since it is often a mistake for 3 or 8.
		char = ('('
				# Must be first to avoid partial matches: e.g., B vs. BR-B
				'AUX|BR-A|BR-B|'
				'A(X|-[1-9])?|'
				'B(X|-[2-58])?|'
				'(D|F|GF|M|NW|P|SN|SR|U)-A|'
				'(D|F|GF|M|SM|SN|SR)-B|'
				'CH|CN|D|FA|FB|GCH|NW|SN|SR|SX|U|X|'
				'“.*?”'
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
		m = re.match(r'^( -\*{1,4}| \*-\*{2,4}| \*{2}-\*{3,4}| \*{3}-\*{4,5}| \*{4}-\*{5})?(?P<extra>.*)$', link)
		if not m:
			return False
		link = m.group('extra')

		# transpose & change
		m = re.match(r'^( tr %s & %s(,| &) ch %s to %s)?(?P<extra>.*)$' % (char, char, char, char), link)
		if not m:
			return False
		link = m.group('extra')

		# transpose & eliminate
		m = re.match(r'^( tr %s & %s and eliminate “.*”)?(?P<extra>.*)$' % (char, char), link)
		if not m:
			return False
		link = m.group('extra')

		# transpose
		m = re.match(r'^( tr %s & %s)?(?P<extra>.*)$' % (char, char), link)
		if not m:
			return False
		link = m.group('extra')

		# change & transpose
		m = re.match(r'^( ch %s to %s & tr %s & %s)?(?P<extra>.*)$' % (char, char, char, char), link)
		if not m:
			return False
		link = m.group('extra')

		# change & add
		m = re.match(r'^( ch %s to %s(, %s to %s)* & add %s)?(?P<extra>.*)$' % (char, char, char, char, char), link)
		if not m:
			return False
		link = m.group('extra')

		# change & eliminate
		m = re.match(r'^( ch %s to %s & eliminate “.*”)?(?P<extra>.*)$' % (char, char), link)
		if not m:
			return False
		link = m.group('extra')

		# change: A to B & X and Y to Z
		m = re.match(r'^( ch %s to %s & %s and %s to %s)?(?P<extra>.*)$' % (char, char, char, char, char), link)
		if not m:
			return False
		link = m.group('extra')

		# change: A to B & LAST X to Y
		m = re.match(r'^( ch %s to %s & last %s to %s)?(?P<extra>.*)$' % (char, char, char, char), link)
		if not m:
			return False
		link = m.group('extra')

		# change
		m = re.match(r'^( ch %s to %s((, %s to %s)* (&|and) %s to %s)?)?(?P<extra>.*)$' % (char, char, char, char, char, char), link)
		if not m:
			return False
		link = m.group('extra')

		# add
		m = re.match(r'^( add %s)?(?P<extra>.*)$' % (char), link)
		if not m:
			return False
		link = m.group('extra')

		# add
		m = re.match(r'^(, (“.*”|(with|son|daughter|mother).*))?$', link)
		if not m:
			return False
		link = ''

		return len(link) == 0

	def verify_conflict_text(self):
		text = ' '.join([x.strip() for x in self.conflict_text])

		done = False
		while not done:
			m = re.match(r'^([^(]*)\(([^)]+)\)(.*)$', text)
			if m:
				pre = m.group(1)
				link = m.group(2)
				post = m.group(3)
				if link[0].isdigit():
					if not self.validate_link(link):
						error('%s: found, but unable to parse: %s' % (self.id, link))
				else:
					print '{0} ignoring parenthetical ({1})'.format(self.id, link)
				text = post
			else:
				done = True

	# Process an entire line from the file.
	def process_line(self, line):
		# Conflicts end on page 190.
		m = re.match(r'^-- page 190$', line)
		if m:
			self.in_conflict_section = False
			return

		# Ignore comments.
		m = re.match(r'^--', line)
		if m:
			return

		# Make sure that all {-tags are valid.
		m = re.match(r'^(.+){', line)
		if m and not m.group(1) in ['B', 'Conflict', 'ConflictGroup', 'ConflictSubGroup']:
			# Allow @{} in the middle of lines.
			if m.group(1)[-1] != '@':
				print line,
				error('Invalid token')

		m = re.match(r'^Conflict{(\d+)}$', line)
		if m:
			self.id = int(m.group(1))
			self.links[self.id] = []
			return

		m = re.match(r'^(\((?P<subid>[a-m])\) )?PRE: (.*)$', line)
		if m:
			self.in_conflict_section = True
			self.in_conflict = True
			self.conflict_text = []
			subid = m.group('subid')
			if not subid:
				subid = '-'
			elif subid != 'a':
				# Make sure previous letter of alphabet is already present.
				prev = self.links[self.id][-1]
				prev_expected = chr(ord(subid) - 1)
				if prev != prev_expected:
					print self.id, subid, prev, prev_expected
			self.links[self.id].append(subid)
			#print 'adding', self.id, subid
			return

		m = re.match(r'^POST: (.*)$', line)
		if m:
			self.in_conflict = False
			self.verify_conflict_text()
			line2 = m.group(1)
			while len(line2) != 0:
				# Q&D regex to catch obviously incorrect chars.
				m = re.match(r'^\(([a-zA-Z\d “”’&\*,;-]*)\) ?(.*)$', line2)
				if m:
					line2 = m.group(2)
					if not self.validate_link(m.group(1)):
						error('%s: found, but unable to parse: %s' % (self.id, m.group(1)))
				else:
					print line2
					error('%s: not found' % self.id)

		if self.in_conflict_section and self.in_conflict:
			self.conflict_text.append(line)


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
