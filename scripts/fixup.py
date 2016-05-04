import os.path
import re
import subprocess
import sys

def error(msg):
	print 'Error: %s' % (msg)
	sys.exit(1)

class Parser():
	"""Conversion/fixup script for Plotto"""

	def __init__(self):
		self.conflict_id = 0

		# Are we parsing in the conflict section.
		self.in_conflict = False
		self.in_subconflict = False

		self.subconflict = []

	def end_subconflict(self):
		if self.in_subconflict and len(self.subconflict) != 0:
			first = True
			in_links = ''
			body = []
			out_links = ''
			for line in self.subconflict:
				if re.match(r'^--', line):
					self.outfile.write(line + '\n')
					continue
				if first:
					in_links = line
					first = False
				elif re.match(r'POST: ', line):
					out_links = line[6:]
				else:
					body.append(line)

			sub_id = ''
			m = re.match(r'^\(([a-n])\) (.*)$', in_links)
			if m:
				sub_id = m.group(1)
				in_links = m.group(2)

			if out_links == '':
				done = False
				in_paren = False
				trim_lines = 0
				trim_chars = 0
				# Extract outlinks from end of body
				for b in reversed(body):
					#print 'b:', b
					if not done:
						n = 0
						for ch in b[::-1]:
							if ch == '(':
								in_paren = False
								n += 1
							elif ch == ')':
								in_paren = True
								n += 1
							elif in_paren or (ch == ' ' and not done):
								n += 1
							else:
								done = True
								break
						# If we found link content, add it to the links.
						if n != 0:
							out_links = ' '.join([b[-n:], out_links])
							#b = b[:-n]
						# If we consumed the entire line, delete it from the body.
						if n == len(b):
							trim_lines += 1
						else:
							# If we didn't consume the entire line, then we're done.
							trim_chars = n
							break

				if trim_lines == len(body):
					error('Unable to find out links for %d' % self.conflict_id)
				if trim_lines != 0:
					del body[-trim_lines:]
				if trim_chars != 0:
					body[-1] = body[-1][:-trim_chars]
				#print 'body', body
				#print 'links "%s"' % out_links.strip()

			if out_links == '':
				out_links = '()'

			if sub_id != '':
				self.outfile.write('(%s) PRE: %s\n' % (sub_id, in_links))
			else:
				self.outfile.write('PRE: %s\n' % in_links)
			for b in body:
				self.outfile.write(b + '\n')
			self.outfile.write('POST: ' + out_links.strip() + '\n')
		self.in_subconflict = False
		self.subconflict = []

	# Process text within a single line.
	def process_text(self, text):
		return text

	# Process an entire line from the file.
	def process_line(self, line):
		# Conflicts end on page 190.
		m = re.match(r'^-- page 190$', line)
		if m:
			self.end_subconflict()
			self.in_conflict = False

		# Start of new B-clause or conflict group ends the current Conflict.
		m = re.match(r'^(B|ConflictGroup|ConflictSubGroup){', line)
		if m:
			self.end_subconflict()
			self.in_conflict = False

		m = re.match(r'^Conflict{(\d+)}$', line)
		if m:
			#print 'Conflict', m.group(1)
			self.conflict_id = int(m.group(1))
			self.end_subconflict()
			self.in_conflict = True
			self.in_subconflict = False

		if self.in_conflict:
			line2 = line.strip();

			# A blank line in a Conflict means that a new (or the first)
			# subconflict will start on the next line.
			if len(line2) == 0 or re.match(r'^--', line2):
				self.end_subconflict()
				self.in_subconflict = True
			elif self.in_subconflict:
				self.subconflict.append(line2)
				return ''

		return self.process_text(line)

	def process(self, src, dst):
		if not os.path.isfile(src):
			error('File "%s" doesn\'t exist' % src)

		try:
			self.infile = open(src, 'r')
		except IOError as e:
			error('Unable to open "%s" for reading: %s' % (src, e))

		try:
			self.outfile = open(dst, 'w')
		except IOError as e:
			error('Unable to open "%s" for writing: %s' % (dst, e))

		for line in self.infile:
			new_line = self.process_line(line)
			self.outfile.write(new_line)

		self.outfile.close()
		self.infile.close()


def main():
	infilename = '../plotto.txt'
	outfilename = '../plotto_new.txt'

	parser = Parser()
	parser.process(infilename, outfilename)

if __name__ == '__main__':
	main()
