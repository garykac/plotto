#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess

configs = [
	'config-mf.txt',
	'config-fm.txt',
	]

for config in configs:
	cmd = ['python', 'build.py', '--config', config]
	subprocess.call(cmd)
