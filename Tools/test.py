#coding: utf8
import random

L = 20000000000

def foo(i):
	if i < 1:
		return True

def foo2(i):
	if i < 1:
		raise RuntimeError("xxx")

def test():
	for i in xrange(L):
		if foo(random.random()):
			pass

def test2():
	for i in xrange(L):
		try:
			foo2(random.random())
		except Exception, e:
			pass

import timeit

print timeit.Timer("test", "from __main__ import test")
print timeit.Timer("test2", "from __main__ import test2")
