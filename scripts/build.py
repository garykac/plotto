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
	"""Build script for Plotto"""

	def __init__(self):
		self.in_conflict = False
		self.id = ''
		self.subid = ''

		self.text = []
		self.links = {}

	def parse_links(self, links):
		while len(links) != 0:
			m = re.match(r'^\((.*?)\) ?(.*)$', links)
			if not m:
				error('%s: invalid link: %s' % (self.id, links))
			if not self.parse_link(m.group(1)):
				error('%s: unable to parse link: %s' % (self.id, links))
			links = m.group(2)

	# Return true if the link is valid.
	def parse_link(self, link):
		# Match character tag.
		# Only match S in certain contexts since it is often a mistake for 3 or 8.
		char = ('('
				# Must be first to avoid partial matches: e.g., B vs. BR-B
				'AUX|BR-A|BR-B|'
				'A(X|-[1-9])?|'
				'B(X|-[2-58])?|'
				'(D|F|GF|M|NW|P|SN|SR|U)-A|'
				'(D|F|GF|M|SM|SN|SR)-B|'
				'CH|CN|D|FA|FB|GCH|NW|SN|SR|SX|U|X|'
				'".*?"'
				')')

		# Sequence: (123; 234)
		if ';' in link:
			links = link.split(';')
			for l in links:
				l = l.strip()
				if not self.parse_link(l):
					return False
			return True

		# Alternation: (123 or 234)
		if ' or ' in link:
			links = link.split(' or ')
			for l in links:
				l = l.strip()
				if not self.parse_link(l):
					return False
			return True

		# ()
		if re.match(r'^$', link):
			return True

		# (123a, b, c)
		m = re.match(r'^(\d+)([a-h](, [a-h])*)?(?P<extra>.*)$', link)
		if not m:
			error('Invalid links: 123a,b,c')
		id = m.group(1)
		subid = m.group(2)
		# Array of [link-id, link-text]s
		links = [[id, id]]
		if subid:
			links = []
			first = True
			for x in subid.split(','):
				x = x.strip()
				if first:
					links.append([id + x, id + x])
					first = False
				else:
					links.append([id + x, x])
		link = m.group('extra')

		# -1-2-3
		m = re.match(r'^(?P<num>(-1)?(-2)?(-3)?(-4)?)(?P<extra>.*)$', link)
		if not m:
			error('Invalid links: -1-2-3')
		if m.group('num'):
			# Can only attach to single links.
			if len(links) != 1:
				error('Too many links for: -1-2-3')
			links[0][1] += m.group('num')
		link = m.group('extra')

		# -*, -**, *-**
		m = re.match(r'^( \*{0,4}-\*{1,5})?(?P<extra>.*)$', link)
		if not m:
			error('Invalid links: -*')
		if m.group(1):
			# Can only attach to single links.
			if len(links) != 1:
				error('Too many links for: -*')
			links[0][1] += m.group(1)
		link = m.group('extra')

		# ⇔ U+21d4
		# ⇄ U+21c4
		# → U+2192

		transpose = []
		change = []
		eliminate = []

		# transpose & change
		m = re.match(r'^(?P<ch> tr (?P<tr1>%s) & (?P<tr2>%s)(,| &) ch (?P<ch1>%s) to (?P<ch2>%s))?(?P<extra>.*)$' % (char, char, char, char), link)
		if not m:
			error('Invalid links: tr & ch')
		if m.group('ch'):
			transpose.append([m.group('tr1'), m.group('tr2')])
			change.append([m.group('ch1'), m.group('ch2')])
		link = m.group('extra')

		# transpose & eliminate
		m = re.match(r'^( tr %s & %s and eliminate ".*")?(?P<extra>.*)$' % (char, char), link)
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
		m = re.match(r'^( ch %s to %s & eliminate ".*")?(?P<extra>.*)$' % (char, char), link)
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
		m = re.match(r'^(, (".*"|(with|son|daughter|mother).*))?$', link)
		if not m:
			return False
		link = ''

		return len(link) == 0

	# Process an entire line from the file.
	def process_line(self, line):
		# Ignore comments.
		m = re.match(r'^--', line)
		if m:
			return

		m = re.match(r'^Conflict{(\d+)}$', line)
		if m:
			self.id = m.group(1)
			self.links[self.id] = []
			self.write_conflict_header()
			return

		m = re.match(r'^(\((?P<subid>[a-m])\) )?PRE: (?P<links>.*)$', line)
		if m:
			self.in_conflict = True
			self.text = []
			subid = m.group('subid')
			if not subid:
				subid = ''
			self.links[self.id].append(subid)

			links = m.group('links')
			self.parse_links(links)
			self.write_conflict_subheader(subid, links)
			return

		m = re.match(r'^POST: (?P<links>.*)$', line)
		if m:
			assert(self.in_conflict)
			self.in_conflict = False
			links = m.group('links')
			self.parse_links(links)
			self.write_conflict_body(links)

		if self.in_conflict:
			self.text.append(line)

	def write_html_header(self):
		self.outfile.write('<html>\n')
		self.outfile.write('<head>\n')
		self.outfile.write('<title>Plotto</title></head>\n')
		self.outfile.write('<meta charset="UTF-8">\n')
		self.outfile.write('<link rel="stylesheet" type="text/css" href="plotto.css"/>\n')
		self.outfile.write('</head>\n')
		self.outfile.write('<body>\n')

	def write_html_footer(self):
		self.outfile.write('</body>\n')
		self.outfile.write('</html>\n')

	def write_conflict_header(self):
		self.outfile.write('\n<div class="conflictid">{0}</div>\n'.format(self.id))

	def write_conflict_subheader(self, subid, links):
		prefix = ''
		if subid != '':
			prefix = '(' + subid + ') '
		self.outfile.write('\n<div class="prelinks">{0} {1}</div>\n'.format(prefix, links))

	def write_conflict_body(self, links):
		self.outfile.write('<div class="desc">')
		for t in self.text:
			self.outfile.write(t)
		self.outfile.write('</div>\n')
		self.outfile.write('<div class="postlinks">{0}</div>\n'.format(links))

	def process(self, src, dst):
		if not os.path.isfile(src):
			error('File "%s" doesn\'t exist' % src)

		try:
			infile = open(src, 'r')
		except IOError as e:
			error('Unable to open "%s" for reading: %s' % (src, e))

		try:
			outfile = open(dst, 'w')
		except IOError as e:
			error('Unable to open "%s" for writing: %s' % (dst, e))

		self.outfile = outfile
		self.write_html_header()
		for line in infile:
			self.process_line(line)
		self.write_html_footer()

		outfile.close()
		infile.close()


def main():
	infilename = '../plotto.txt'
	outfilename = '../plotto.html'

	parser = Parser()
	parser.process(infilename, outfilename)

if __name__ == '__main__':
	main()
