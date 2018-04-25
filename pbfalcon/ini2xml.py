#!/usr/bin/env python2.7
"""Convert our cfg file to preset.xml section.

This is not part of the workflow. It is only a utility, used as needed.

https://github.com/PacificBiosciences/FALCON-pbsmrtpipe/issues/2
"""
from __future__ import absolute_import
import ConfigParser
import contextlib
import pprint
import sys

def parse_config(ifp):
    config = ConfigParser.ConfigParser()
    config.readfp(ifp)
    return config

def get_dict(cfg, sec='General'):
    return dict((key, val) for key, val in cfg.items(sec))

def dump(ofp, data):
    indent = '    '
    n = [1]
    def writeln(msg):
        ofp.write(indent*n[0] + msg + '\n')

    @contextlib.contextmanager
    def xml(tag, **attrs):
        extra = ''.join(' {}="{}"'.format(k, v) for k,v in attrs.iteritems())
        writeln('<{}{}>'.format(tag, extra))
        n[0] += 1
        yield
        n[0] -= 1
        writeln('</{}>'.format(tag))

    with xml('task-options'):
        prefix = 'falcon_ns.task_options.'
        for key, val in sorted(data.iteritems()):
            attrs = dict([('id', prefix+key)])
            with xml('option', **attrs):
                with xml('value'):
                    writeln(val)

def convert(ifp, ofp):
    config = parse_config(ifp)
    data = get_dict(config)
    dump(ofp, data)

def main():
    args = sys.argv[1:]
    if args:
        raise Exception(usage)
    ifs = sys.stdin
    ofs = sys.stdout
    convert(ifs, ofs)

usage = """Usage:
  ini2xml < file.ini > file.xml
"""

if __name__=="__main__":
    main(*sys.argv[1:])
