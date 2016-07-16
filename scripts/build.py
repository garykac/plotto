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

		self.group = ''
		self.subgroup = ''

		self.bclause_id = ''
		self.bclause_name = ''
		self.id = ''
		self.subid = ''

		self.text = []
		self.links = {}

	def parse_links(self, links):
		hyperlinks = ''
		while len(links) != 0:
			m = re.match(r'^\((.*?)\) ?(.*)$', links)
			if not m:
				error('%s: invalid link: %s' % (self.id, links))
			hlink = self.parse_link(m.group(1))
			if hlink == None:
				error('%s: unable to parse link: %s' % (self.id, links))
			if hyperlinks != '':
				hyperlinks += ' '
			hyperlinks += '<span class="clinkgroup">{0}</span>'.format(hlink)
			links = m.group(2)
		return hyperlinks

	# Return the HTML hyperlink for this link.
	# Assumes all links are valid (since they were all checked by verify.py).
	def parse_link(self, link):
		orig_link = link
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
			hlinks = []
			for l in links:
				l = l.strip()
				hlink = self.parse_link(l)
				if hlink == None:
					return None
				hlinks.append(hlink)
			return ' ; '.join(hlinks)

		# Alternation: (123 or 234)
		if ' or ' in link:
			links = link.split(' or ')
			hlinks = []
			for l in links:
				l = l.strip()
				hlink = self.parse_link(l)
				if hlink == None:
					return None
				hlinks.append(hlink)
			return ' or '.join(hlinks)

		# ()
		if re.match(r'^$', link):
			return ''

		# (123a, b, c)
		m = re.match(r'^(\d+)([a-h](, [a-h])*)?(?P<extra>.*)$', link)
		if not m:
			error('Invalid links: 123a,b,c')
		id = m.group(1)
		subid = m.group(2)

		return '<a href="#{0}" class="clink">{1}</a>'.format(id, orig_link)

	# Process an entire line from the file.
	def process_line(self, line):
		# Ignore comments.
		m = re.match(r'^--', line)
		if m:
			return

		m = re.match(r'^ConflictGroup{(.+)}$', line)
		if m:
			self.group = m.group(1)
			return

		m = re.match(r'^ConflictSubGroup{(.+)}$', line)
		if m:
			self.subgroup = m.group(1)
			self.write_group_header(self.group)
			self.write_subgroup_header(self.subgroup)
			return

		m = re.match(r'^B{(\d+)} (.*)$', line)
		if m:
			self.bclause_id = m.group(1)
			self.bclause_name = m.group(2)
			self.write_bclause_header(self.bclause_id, self.bclause_name)
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
			hlinks = self.parse_links(links)
			self.write_conflict_subheader(subid, hlinks)
			return

		m = re.match(r'^POST: (?P<links>.*)$', line)
		if m:
			assert(self.in_conflict)
			self.in_conflict = False
			links = m.group('links')
			hlinks = self.parse_links(links)
			self.write_conflict_body(hlinks)

		if self.in_conflict:
			self.text.append(line)

	def write_html_header(self):
		self.outfile.write('<!DOCTYPE html>\n')
		self.outfile.write('<html lang="en">\n')
		self.outfile.write('<head>\n')
		self.outfile.write('\t<meta charset="utf-8">\n')
		self.outfile.write('\t<meta http-equiv="X-UA-Compatible" content="IE=edge">\n')
		self.outfile.write('\t<meta name="viewport" content="width=device-width, initial-scale=1">\n')
		self.outfile.write('\t<title>Plotto</title></head>\n')
		self.outfile.write('\t<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">\n')
		self.outfile.write('\t<link rel="stylesheet" type="text/css" href="plotto.css"/>\n')
		self.outfile.write('\t<link href="https://fonts.googleapis.com/css?family=Old+Standard+TT:400,400italic,700" rel="stylesheet" type="text/css">\n')
		self.outfile.write('</head>\n')
		self.outfile.write('<body>\n')

		self.write_navbar()

		self.outfile.write('<div class="container">\n')

	def write_html_footer(self):
		self.outfile.write('</div>\n')
		self.outfile.write('</body>\n')
		self.outfile.write('</html>\n')

	def write_navbar(self):
		self.outfile.write('<nav class="navbar navbar-inverse navbar-static-top">\n')
		self.outfile.write('\t<div class="container">\n')
		self.outfile.write('\t\t<div class="navbar-header">\n')
		self.outfile.write('\t\t\t<a class="navbar-brand" href="./plotto.html">Plotto - A New Method of Plot Suggestion for Writers of Creative Fiction</a>\n')
		self.outfile.write('\t\t</div>\n')
		self.outfile.write('\t</div>\n')
		self.outfile.write('</nav>\n')

	def write_group_header(self, name):
		self.outfile.write('\n<div class="group">{0}</div>\n'.format(name))

	def write_subgroup_header(self, name):
		self.outfile.write('\n<div class="subgroup">{0}</div>\n'.format(name))

	def write_bclause_header(self, id, name):
		self.outfile.write('\n<div class="bclause">({0}) {1}</div>\n'.format(id, name))

	def write_conflict_header(self):
		self.outfile.write('\n<div class="conflictid" id="{0}">{1}</div>\n'.format(self.id, self.id))

	def write_conflict_subheader(self, subid, links):
		prefix = ''
		if subid != '':
			prefix = '<span class="subid">' + subid + '</span> '
		self.outfile.write('\n<div class="prelinks">{0}{1}</div>\n'.format(prefix, links))

	def write_conflict_body(self, links):
		self.outfile.write('<div class="desc">')
		text = ' '.join([x.strip() for x in self.text])
		new_text = ''
		done = False
		while not done:
			m = re.match(r'^([^(]*)\(([^)]+)\)(.*)$', text)
			if m:
				pre = m.group(1)
				link = m.group(2)
				post = m.group(3)
				if link[0].isdigit():
					hlink = self.parse_links('({0})'.format(link))
					if hlink == None:
						error('{0}: found, but unable to parse: {1}'.format(self.id, link))
				else:
					hlink = '({0})'.format(link)

				new_text += self.add_tags(pre) + hlink
				text = post
			else:
				new_text += self.add_tags(text)
				done = True
		self.outfile.write(new_text)
		self.outfile.write('</div>\n')
		self.outfile.write('<div class="postlinks">{0}</div>\n'.format(links))

	def add_tags(self, text):
		#m = re.match(r'^(.*)A-5(.*)$', text)
		#if m:
		#	text = self.add_tags(m.group(1))
		#	text += '<span class="character" title="tooltip">A-5</span>'
		#	text += self.add_tags(m.group(2))
		return text

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
