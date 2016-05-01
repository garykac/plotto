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
		# Are we parsing in the conflict section.
		self.in_conflict = False
		self.next_conflict_id = 1

	# Process text within a single line.
	def process_text(self, text):
		return text

	# Process an entire line from the file.
	def process_line(self, line):
		m = re.match(r'^-- page 18$', line)
		if m:
			self.in_conflict = True

		m = re.match(r'^-- page 190$', line)
		if m:
			self.in_conflict = False

		if self.in_conflict:
			m = re.match(r'^(\d+)$', line)
			if m:
				id = int(m.group(1))
				if id != self.next_conflict_id:
					error('Unexpected conflict id: %d. Expected %d' % (id, self.next_conflict_id))
				self.next_conflict_id += 1
				return 'Conflict{%d}\n' % id

		return self.process_text(line)

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

		for line in infile:
			new_line = self.process_line(line)
			outfile.write(new_line)

		outfile.close()
		infile.close()


def main():
	infilename = '../plotto.txt'
	outfilename = '../plotto_new.txt'

	parser = Parser()
	parser.process(infilename, outfilename)

if __name__ == '__main__':
	main()
