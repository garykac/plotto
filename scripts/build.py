#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Run this script from within the scripts/ directory.

import getopt
import os.path
import re
import sys

def error(msg):
	print 'Error: %s' % (msg)
	sys.exit(1)

# These terms are bidirectional unless marked with an '*'. In this case, then '*'ed
# term is not replaced with the other term (although the other term will be replaced with
# the '*'ed term).
# 'her' always requires disambiguation, so there is no default substitution.
#   her: objective (him) vs. possessive (his)
genderedTerms = [
	['adventurer', 'adventuress'],
	['brother', 'sister'],
	['brothers', 'sisters'],
	['boy', 'girl'],
	['clergyman', 'clergywoman'],
	['cowboy', 'cowgirl'],
	['craftsman', 'craftswoman'],
	['father', 'mother'],
	['fatherhood', 'motherhood'],
	['fathers', 'mothers'],
	['foreman', 'forewoman'],
	['frontiersman', 'frontierswoman'],
	['gentleman', 'lady'],
	# Handle gentlemen's <- ladies' (ladies' is preprocessed into ladies_poss)
	["*gentlemen's", "ladies_poss"],
	['gentlemen', 'ladies'],
	['grandfather', 'grandmother'],
	['he', 'she'],
	['highwayman', 'highwaywoman'],
	# him -> her
	# See comment at top for her -> his/him
	['him', '*her'],
	['himself', 'herself'],
	# wife <-> husband
	# husband: spouse (wife) vs. to manage
	# husband converts by default to 'wife', needs annotation to remain unchanged (=to manage)
	['husband', 'wife'],
	# his -> her
	# See comment at top for her -> his/him
	['his', '*her'],
	['male', 'female'],
	['man', 'woman'],
	['man-hater', 'woman-hater'],
	['mankind', 'womankind'],
	['manly', 'womanly'],
	['manservant', 'maid'],
	['men', 'women'],
	['misogynist', 'misandrist'],
	# lover <- mistress
	# 'lover' is ungendered and is not converted into 'mistress'
	# mistress: head of household (master) vs. lover
	# 'mistress' converts by default to 'lover', needs annotation for 'master'
	['*lover', 'mistress'],
	['nephew', 'niece'],
	['paternal', 'maternal'],
	['policeman', 'policewoman'],
	['son', 'daughter'],
	['stepfather', 'stepmother'],
	['uncle', 'aunt'],
	# unmarried <- maiden
	# 'unmarried' is ungendered and is left unchanged
	# This mapping works because 'maiden' is only used as an adj, as in 'maiden aunt'
	# and 'maiden sisters'. The noun form of 'maiden' is not used.
	['*unmarried', 'maiden'],
	['widower', 'widow'],
	# cad: female equivalent?
]

# Gendered character abbreviations.
# These don't need to be swapped, but it is more readable to do so.
genderedChars = [
	['F', 'M'],		# father mother
	['BR', 'SR'],	# brother sister
	['SN', 'D'],	# son daughter
	['U', 'AU'],	# uncle aunt
	['NW', 'NC'],	# nephew niece
	['GF', 'GM'],	# grandfather grandmother
	['SF', 'SM'],	# stepfather stepmother
]

class Parser():
	"""Build script for Plotto"""

	def __init__(self):
		self.A = 'm'
		self.B = 'f'

		self.page = 0
		self.in_conflict_section = False
		self.in_conflict_div = False
		self.in_conflict = False

		self.group = ''
		self.subgroup = ''

		self.bclause_id = ''
		self.bclause_name = ''
		self.id = ''
		self.subid = ''

		self.text = []
		self.links = {}

		self.format_paragraph = None
		self.format_lines = None
		self.format_next_line = None
		self.format_links = None
		self.blank_line = False
		
		self.next_id = None

		self.js_files = []
		self.css_files = []
		self.enable_bootstrap = True
		
		# Dict with count of all words found in doc.
		self.dict = {}
		
		# Arrays to swap gendered character abbreviations.
		self.swapCharList = {}
		for x in genderedChars:
			male = x[0]
			female = x[1]
			assert not (male in self.swapCharList)
			self.swapCharList[male] = female
			assert not (female in self.swapCharList)
			self.swapCharList[female] = male

		# Array to swap gendered terms for equivalent in opposite gender.
		self.replaceList = {}
		for x in genderedTerms:
			male = x[0]
			female = x[1]
			m2f = True
			f2m = True
			if male[0] == '*':
				male = male[1:]
				m2f = False
			if female[0] == '*':
				female = female[1:]
				f2m = False

			if m2f:
				assert not (male in self.replaceList)
				self.replaceList[male] = female
			if f2m:
				assert not (female in self.replaceList)
				self.replaceList[female] = male

		# The pronoun 'her' can be either the objective (cf. him) or the
		# possessive (cf. his). By default, we assume the posssive, but the
		# "-- HER (obj|poss)" comment can be used to override that default.
		# This is an array of 'obj', 'poss' since 'her' can occur multiple
		# time on the same line.
		self.her_info = None

		# Capital 'A' can either be the character A, or, at the beginning of a
		# sentence, it can be the determiner 'a'. By default, it is assumed to
		# be the character.
		self.a_info = None

		# Capital 'U' can either be the character U, or it can be part of an
		# abbreviation (like U.S.). By default, it is assumed to be the character.
		self.u_info = None

		# 'husband' can be either a noun or a verb. By default, it is a noun,
		# but the "-- HUSBAND verb" comment can be used to override that default.
		self.husband_info = None

		# 'mistress' can be either a head of household or a lover (default).
		# Use "-- MISTRESS master" to override default
		self.mistress_info = None

	def setAB(self, ab):
		self.A = ab[0]
		self.B = ab[1]

	def setJavascript(self, js):
		if isinstance(js, basestring):
			self.js_files = [js]
		else:
			self.js_files = js
		
	def setCss(self, css):
		if isinstance(css, basestring):
			self.css_files = [css]
		else:
			self.css_files = css

	def enableBootstrap(self, enable):
		self.enableBootstrap = enable
			
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
			error('Invalid links: {0}'.format(orig_link))
		id = m.group(1)
		subid = m.group(2)

		orig_link = orig_link.replace("&", "&amp;")
		return '<a href="#{0}" class="clink">{1}</a>'.format(id, orig_link)

	# Process an entire line from the file.
	def process_line(self, line):
		# Reset language defaults.
		self.her_info = None
		self.a_info = None
		self.u_info = None
		self.husband_info = None
		self.mistress_info = None

		# Process comments.
		m = re.match(r'^--', line)
		if m:
			m = re.match(r'-- page (\d+)', line)
			if m:
				self.page = m.group(1)

				if self.page == '18':
					self.in_conflict_section = True
					self.outfile.write('</div>\n')  # End the 'frontmatter' section
				if self.page == '190':
					self.in_conflict_section = False
					self.id = ''

			m = re.match(r'-- HER (.*)', line)
			if m:
				self.her_info = m.group(1).split()
			m = re.match(r'-- A (.*)', line)
			if m:
				self.a_info = m.group(1).split()
			m = re.match(r'-- U (.*)', line)
			if m:
				self.u_info = m.group(1).split()
			if line == '-- HUSBAND verb':
				self.husband_info = 'verb'
			if line == '-- MISTRESS master':
				self.mistress_info = 'master'

			m = re.match(r'^-- ID:(.*)', line)
			if m:
				self.next_id = m.group(1)
				return

			m = re.match(r'^-- FORMAT_LINES:(.*)', line)
			if m:
				# Put blank div between multiple FORMAT_LINES chunks.
				if self.format_lines != None:
					self.outfile.write('<div class="space">&nbsp;</div>\n')

			m = re.match(r'^-- FORMAT', line)
			if m:
				# Any new format command cancels previous formatting.
				self.format_paragraph = None
				self.format_lines = None
				self.format_next_line = None
				self.format_links = None
				# Fall through

			# FORMAT_BEGIN must be followed by FORMAT_END
			m = re.match(r'^-- FORMAT_BEGIN:(.*)', line)
			if m:
				self.format_paragraph = m.group(1)
				self.outfile.write('<div class="{0}">\n'.format(self.format_paragraph))
				return
			m = re.match(r'^-- FORMAT_END', line)
			if m:
				self.outfile.write('</div>\n')
				return

			m = re.match(r'^-- FORMAT:(.*)', line)
			if m:
				self.format_next_line = m.group(1)
				return
			m = re.match(r'^-- FORMAT_LINES:(.*)', line)
			if m:
				if self.format_lines != None:
					self.outfile.write('<div>xxx</div>\n')
				self.format_lines = m.group(1)
				return
			m = re.match(r'^-- FORMAT_LINKS:(.*)', line)
			if m:
				self.format_links = m.group(1)
				return
			m = re.match(r'^-- HR', line)
			if m:
				self.outfile.write('<hr/>\n')
				return
			return

		if self.format_paragraph:
			if line == '':
				if not self.blank_line:
					self.outfile.write('</div>\n<div class="{0}">\n'.format(self.format_paragraph))
					self.blank_line = True
			else:
				self.outfile.write('{0}\n'.format(self.add_tags(line)))
				self.blank_line = False
			return

		if self.format_lines:
			self.outfile.write('<div class="{0}">{1}</div>\n'.format(self.format_lines, self.add_tags(line)))
			return

		if self.format_next_line:
			id = ''
			if self.next_id:
				id = ' id="{0}"'.format(self.next_id)
			self.outfile.write('<div{2} class="{0}">{1}</div>\n'.format(self.format_next_line, line, id))
			self.format_next_line = None
			self.next_id = None
			return

		if self.format_links:
			prefix = ''
			m = re.match('^\s*\(([a-d])\) (.*)$', line)
			if m:
				prefix = '<span class="subid">{0}</span>'.format(m.group(1))
				line = m.group(2)
			self.outfile.write('<div class="{0}">{1}{2}</div>\n'.format(self.format_links, prefix, self.parse_links(line)))
			self.format_links = None
			return

		if self.in_conflict_section:
			if line == '':
				return

			m = re.match(r'^ConflictGroup{(.+)}$', line)
			if m:
				self.group = m.group(1)
				return

			m = re.match(r'^ConflictSubGroup{(.*)}$', line)
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
				if self.in_conflict_div:
					self.write_conflict_footer()
				self.write_conflict_header()
				return

			m = re.match(r'^(\((?P<subid>[a-m])\) )?PRE: (?P<links>.*)$', line)
			if m:
				assert(not self.in_conflict)
				self.in_conflict = True
				self.text = []
				self.subid = m.group('subid')
				if not self.subid:
					self.subid = ''
				self.links[self.id].append(self.subid)

				links = m.group('links')
				hlinks = self.parse_links(links)
				self.write_conflict_subheader(self.subid, hlinks)
				return

			m = re.match(r'^POST: (?P<links>.*)$', line)
			if m:
				assert(self.in_conflict)
				self.in_conflict = False
				links = m.group('links')
				hlinks = self.parse_links(links)
				self.write_conflict_body(hlinks)
				self.subid = ''
				return

			if not self.in_conflict:
				print line
				assert(self.in_conflict)
			self.text.append(line)

	def write_html_header(self):
		self.outfile.write('<!DOCTYPE html>\n')
		self.outfile.write('<html lang="en">\n')
		self.outfile.write('<head>\n')
		self.outfile.write('\t<meta charset="utf-8" />\n')
		self.outfile.write('\t<meta http-equiv="X-UA-Compatible" content="IE=edge" />\n')
		self.outfile.write('\t<meta name="viewport" content="width=device-width, initial-scale=1" />\n')
		self.outfile.write('\t<title>Plotto</title>\n')
		if self.enable_bootstrap:
			self.outfile.write('\t<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous" />\n')
		for css in self.css_files:
			self.outfile.write('\t<link rel="stylesheet" type="text/css" href="css/%s" />\n' % css)
		self.outfile.write('\t<link href="https://fonts.googleapis.com/css?family=Old+Standard+TT:400,400italic,700" rel="stylesheet" type="text/css" />\n')
		for js in self.js_files:
			self.outfile.write('\t<script src="js/%s" ></script>\n' % js)
		self.outfile.write('</head>\n')
		self.outfile.write('<body>\n')

		self.write_navbar()

		self.outfile.write('<div class="container">\n')
		self.outfile.write('<div class="frontmatter">\n')

	def write_html_footer(self):
		self.outfile.write('</div>\n')
		if self.enable_bootstrap:
			self.outfile.write('<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.3/jquery.min.js"></script>\n')
			self.outfile.write('<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script>\n')
		self.outfile.write('</body>\n')
		self.outfile.write('</html>\n')

	def write_navbar(self):
		self.outfile.write('<nav class="navbar navbar-inverse navbar-static-top">\n')
		self.outfile.write('\t<div class="container">\n')
		self.outfile.write('\t\t<div class="navbar-header">\n')
		self.outfile.write('\t\t\t<a class="navbar-brand" href="./plotto.html">Plotto - A New Method of Plot Suggestion for Writers of Creative Fiction</a>\n')
		self.outfile.write('\t\t</div>\n')

		self.outfile.write('\t\t<div class="collapse navbar-collapse" id="navbar-right">\n')
		self.outfile.write('\t\t<ul class="nav navbar-nav navbar-right">\n')
		self.outfile.write('\t\t<li class="dropdown">\n')
		self.outfile.write('\t\t\t<a href="#" class="dropdown-toggle" data-toggle="dropdown" role="button" aria-haspopup="true" aria-expanded="false">AB <span class="caret"></span></a>\n')
		self.outfile.write('\t\t\t<ul class="dropdown-menu">\n')
		self.outfile.write('\t\t\t\t<li><a href="plotto-mf.html">A=male, B=female</a></li>\n')
		self.outfile.write('\t\t\t\t<li><a href="plotto-fm.html">A=female, B=male</a></li>\n')
		self.outfile.write('\t\t\t</ul>\n')
		self.outfile.write('\t\t</li>\n')
		self.outfile.write('\t\t</ul>\n')
		self.outfile.write('\t\t</div>\n')

		self.outfile.write('\t</div>\n')
		self.outfile.write('</nav>\n')

	def write_group_header(self, name):
		self.outfile.write('\n<div class="group">{0}</div>\n'.format(name))

	def write_subgroup_header(self, name):
		if name != '':
			self.outfile.write('\n<div class="subgroup">{0}</div>\n'.format(name))

	def write_bclause_header(self, id, name):
		self.outfile.write('\n<div class="bclause">({0}) {1}</div>\n'.format(id, name))

	def write_conflict_header(self):
		self.outfile.write('\n<div class="conflict" id="{0}">\n'.format(self.id))
		self.in_conflict_div = True
		self.outfile.write('\n<div class="conflictid">{0}</div>\n'.format(self.id))

	def write_conflict_footer(self):
		self.outfile.write('\n</div>\n')
		self.in_conflict_div = False

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
		m = re.match(r'^(.*)@{(.+)}(.*)$', text)
		if m:
			text = self.add_tags(m.group(1))
			text += self.parse_link(m.group(2))
			text += self.add_tags(m.group(3))
		return text

	# Preprocess the word, swapping gendered terms.
	def preprocess_word(self, word):
		if word == '':
			return word

		char = word.split('-')
		if len(char) == 2:
			(pre, post) = char
			if post == 'A' or post == 'B':
				if pre in self.swapCharList:
					return '%s-%s' % (self.swapCharList[pre], post)
		
		if word == 'U' and self.u_info:
			return word

		if word in ['BR', 'SR', 'SN', 'D', 'U', 'AU', 'NC', 'NW']:
			return self.swapCharList[word]
		
		cap = False
		wordLower = word
		if word[0].isupper():
			cap = True
			wordLower = word[0].lower() + word[1:]

		if wordLower == 'her':
			wordNew = 'his'
			if self.her_info != None:
				if len(self.her_info) == 0:
					print self.page, self.id, 'missing her info'
				type = self.her_info.pop(0)
				if type == 'obj':
					wordNew = 'him'
				elif type == 'poss':
					wordNew = 'his'
				else:
					assert False
			if cap:
				wordNew = wordNew[0].upper() + wordNew[1:]
			return wordNew

		if wordLower == 'husband' and self.husband_info:
			return 'husband'
		if wordLower == 'mistress' and self.mistress_info:
			return 'master'

		if wordLower in self.replaceList:
			wordNew = self.replaceList[wordLower]
			if cap:
				wordNew = wordNew[0].upper() + wordNew[1:]
			return wordNew
		return word

	def preprocess_line(self, line):
		if line[0:2] == '--':
			return line
		# Preprocess "ladies'" so we can convert to "gentlemen's".
		line = line.replace("ladies'", "ladies_poss");
		# Note: — is emdash
		words = re.split('([ .,:;—\'"\(\)\[\]\{\}])', line)
		for w in words:
			#if self.id == '1289':
			#	print self.subid, w
			self.add_to_dict(w, line)
		line2 = ''.join([self.preprocess_word(w) for w in words])
		return line2

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
			line = line.strip()
			if self.A == 'f' and self.B == 'm':
				line = self.preprocess_line(line)
			self.process_line(line)
		if self.in_conflict_div:
			self.write_conflict_footer()
		self.write_html_footer()

		outfile.close()
		infile.close()

	def add_to_dict(self, word, line):
		if re.match(r'^Conflict?{\d+}$', word):
			return
		if re.match(r'^[@B]{\d+}$', word):
			return
		if re.match(r'^\(?[-\d]+[abcde]?\)?$', word):
			return
		# Print entire line for word.
		# Useful for tracking down short typo words.
		#if word == 'hom':
		#	print self.id, line

		if not word in self.dict:
			self.dict[word] = 0
		self.dict[word] += 1

	def write_dict(self):
		dst = 'dict.txt'
		try:
			outfile = open(dst, 'w')
		except IOError as e:
			error('Unable to open "%s" for writing: %s' % (dst, e))

		for word in sorted(self.dict, key=self.dict.get, reverse=True):
			outfile.write('%d %s\n' % (self.dict[word], word))

		outfile.close()

def usage():
	print 'Usage: %s <options>' % sys.argv[0]
	print 'where <options> are:'
	print '  --config <config-file-name>'
	print '  --dict'  # write word frequency dict
	print '  --verbose'  # verbose debug output
	
def load_config(file):
	config = {}
	try:
		config_file = open(file, 'r')
	except IOError as e:
		error('Unable to open config file "%s": %s' % (file, e))
	
	for line in config_file:
		line = line.strip()
		if line == '' or line[0] == '#':
			continue
		(k,v) = line.split('=')
		if v == 'True':
			config[k] = True
		elif v == 'False':
			config[k] = False
		elif ',' in v:
			config[k] = v.split(',')
		else:
			config[k] = v
		
	config_file.close()
	return config

def main():
	try:
		opts, args = getopt.getopt(sys.argv[1:],
			'c:dv',
			['config=', 'dict', 'verbose'])
	except getopt.GetoptError:
		usage()
		exit()

	config_file = None
	write_dict = False
	verbose = False
	
	for opt, arg in opts:
		if opt in ('-c', '--config'):
			config_file = arg
		elif opt in ('-d', '--dict'):
			write_dict = True
		elif opt in ('-v', '--verbose'):
			verbose = True

	if config_file:
		config = load_config(config_file)
	else:
		# Default configuration
		config = {}
		config['output_file'] = '../plotto.html'
		config['gender_swap'] = False
		config['javascript'] = 'random.js'
		config['css'] = 'plotto.css'
		config['include_bootstrap'] = True
	#print config
		
	# The raw input file (with the Plotto text).
	infilename = '../plotto.txt'
	gender = 'mf'
	if config['gender_swap']:
		gender = 'fm'

	print 'Building', config['output_file'], '...'
	
	parser = Parser()
	parser.setAB(gender)
	parser.setJavascript(config['javascript'])
	parser.setCss(config['css'])
	parser.enableBootstrap(config['include_bootstrap'])
	parser.process(infilename, config['output_file'])
	if write_dict:
		parser.write_dict()
	
if __name__ == '__main__':
	main()
