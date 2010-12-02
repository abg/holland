# -*- coding: utf8 -*-
""" EntryPoints, extracted from setuptools pkg_resources
"""
import os
import re

MODULE   = re.compile(r"\w+(\.\w+)*$").match
DISTRO   = re.compile(r"\s*((\w|[-.])+)").match    # Distribution or extra
OBRACKET = re.compile(r"\s*\[").match
CBRACKET = re.compile(r"\s*\]").match
VERSION  = re.compile(r"\s*(<=?|>=?|==|!=)\s*((\w|[-.])+)").match  # ver. info
LINE_END = re.compile(r"\s*(#.*)?$").match         # whitespace and comment
CONTINUE = re.compile(r"\s*\\\s*(#.*)?$").match    # line continuation
COMMA    = re.compile(r"\s*,").match               # comma between items

class Requirement:
    def __init__(self, project_name, specs, extras):
        """DO NOT CALL THIS UNDOCUMENTED METHOD; use Requirement.parse()!"""
        self.unsafe_name, project_name = project_name, safe_name(project_name)
        self.project_name, self.key = project_name, project_name.lower()
        index = [(parse_version(v),state_machine[op],op,v) for op,v in specs]
        index.sort()
        self.specs = [(op,ver) for parsed,trans,op,ver in index]
        self.index, self.extras = index, tuple(map(safe_extra,extras))
        self.hashCmp = (
            self.key, tuple([(op,parsed) for parsed,trans,op,ver in index]),
            frozenset(self.extras)
        )
        self.__hash = hash(self.hashCmp)

    def __str__(self):
        specs = ','.join([''.join(s) for s in self.specs])
        extras = ','.join(self.extras)
        if extras: extras = '[%s]' % extras
        return '%s%s%s' % (self.project_name, extras, specs)

    def __eq__(self,other):
        return isinstance(other,Requirement) and self.hashCmp==other.hashCmp

    def __contains__(self,item):
        if isinstance(item,Distribution):
            if item.key != self.key: return False
            if self.index: item = item.parsed_version  # only get if we need it
        elif isinstance(item,basestring):
            item = parse_version(item)
        last = None
        for parsed,trans,op,ver in self.index:
            action = trans[cmp(item,parsed)]
            if action=='F':     return False
            elif action=='T':   return True
            elif action=='+':   last = True
            elif action=='-' or last is None:   last = False
        if last is None: last = True    # no rules encountered
        return last


    def __hash__(self):
        return self.__hash

    def __repr__(self): return "Requirement.parse(%r)" % str(self)

    def parse(s):
        reqs = list(parse_requirements(s))
        if reqs:
            if len(reqs)==1:
                return reqs[0]
            raise ValueError("Expected only one requirement", s)
        raise ValueError("No requirements found", s)

    parse = staticmethod(parse)

def yield_lines(strs):
    """Yield non-empty/non-comment lines of a ``basestring`` or sequence"""
    if isinstance(strs,basestring):
        for s in strs.splitlines():
            s = s.strip()
            if s and not s.startswith('#'):     # skip blank lines/comments
                yield s
    else:
        for ss in strs:
            for s in yield_lines(ss):
                yield s

def parse_requirements(strs):
    """Yield ``Requirement`` objects for each specification in `strs`

    `strs` must be an instance of ``basestring``, or a (possibly-nested)
    iterable thereof.
    """
    # create a steppable iterator, so we can handle \-continuations
    lines = iter(yield_lines(strs))

    def scan_list(ITEM, TERMINATOR, line, p, groups, item_name):
        items = []
        while not TERMINATOR(line,p):
            if CONTINUE(line,p):
                try:
                    line = lines.next(); p = 0
                except StopIteration:
                    raise ValueError(
                        "\\ must not appear on the last nonblank line"
                    )
            match = ITEM(line,p)
            if not match:
                raise ValueError("Expected "+item_name+" in",line,"at",line[p:])
            items.append(match.group(*groups))
            p = match.end()
            match = COMMA(line,p)
            if match:
                p = match.end() # skip the comma
            elif not TERMINATOR(line,p):
                raise ValueError(
                    "Expected ',' or end-of-list in",line,"at",line[p:]
                )

        match = TERMINATOR(line,p)
        if match: p = match.end()   # skip the terminator, if any
        return line, p, items

    for line in lines:
        match = DISTRO(line)
        if not match:
            raise ValueError("Missing distribution spec", line)
        project_name = match.group(1)
        p = match.end()
        extras = []

        match = OBRACKET(line,p)
        if match:
            p = match.end()
            line, p, extras = scan_list(
                DISTRO, CBRACKET, line, p, (1,), "'extra' name"
            )

        line, p, specs = scan_list(VERSION,LINE_END,line,p,(1,2),"version spec")
        specs = [(op,safe_version(val)) for op,val in specs]
        yield Requirement(project_name, specs, extras)


class EntryPoint(object):
    """Object representing an advertised importable object"""

    def __init__(self, name, module_name, attrs=(), extras=(), dist=None):
        if not MODULE(module_name):
            raise ValueError("Invalid module name", module_name)
        self.name = name
        self.module_name = module_name
        self.attrs = tuple(attrs)
        self.extras = Requirement.parse(("x[%s]" % ','.join(extras))).extras
        self.dist = dist

    def __str__(self):
        s = "%s = %s" % (self.name, self.module_name)
        if self.attrs:
            s += ':' + '.'.join(self.attrs)
        if self.extras:
            s += ' [%s]' % ','.join(self.extras)
        return s

    def __repr__(self):
        return "EntryPoint.parse(%r)" % str(self)

    def load(self):
        """Loads the entry point."""
        entry = __import__(self.module_name, globals(),
                           globals(), ['__name__'])
        for attr in self.attrs:
            try:
                entry = getattr(entry,attr)
            except AttributeError:
                raise ImportError("%r has no %r attribute" % (entry,attr))
        return entry

    @classmethod
    def parse(cls, src, dist=None):
        """Parse a single entry point from string `src`

        Entry point syntax follows the form::

            name = some.module:some.attr [extra1,extra2]

        The entry name and module name are required, but the ``:attrs`` and
        ``[extras]`` parts are optional
        """
        try:
            attrs = extras = ()
            name,value = src.split('=',1)
            if '[' in value:
                value,extras = value.split('[',1)
                req = Requirement.parse("x["+extras)
                if req.specs: raise ValueError
                extras = req.extras
            if ':' in value:
                value,attrs = value.split(':',1)
                if not MODULE(attrs.rstrip()):
                    raise ValueError
                attrs = attrs.rstrip().split('.')
        except ValueError:
            raise ValueError(
                "EntryPoint must be in 'name=module:attrs [extras]' format",
                src
            )
        else:
            return cls(name.strip(), value.strip(), attrs, extras, dist)

    @classmethod
    def parse_group(cls, group, lines, dist=None):
        """Parse an entry point group"""
        if not MODULE(group):
            raise ValueError("Invalid group name", group)
        this = {}
        for line in yield_lines(lines):
            ep = cls.parse(line, dist)
            if ep.name in this:
                raise ValueError("Duplicate entry point", group, ep.name)
            this[ep.name]=ep
        return this

    @classmethod
    def parse_map(cls, data, dist=None):
        """Parse a map of entry point groups"""
        if isinstance(data,dict):
            data = data.items()
        else:
            data = split_sections(data)
        maps = {}
        for group, lines in data:
            if group is None:
                if not lines:
                    continue
                raise ValueError("Entry points must be listed in groups")
            group = group.strip()
            if group in maps:
                raise ValueError("Duplicate group name", group)
            maps[group] = cls.parse_group(group, lines, dist)
        return maps

def split_sections(s):
    """Split a string or iterable thereof into (section, content) pairs

    Each ``section`` is a stripped version of the section header ("[section]")
    and each ``content`` is a list of stripped lines excluding blank lines and
    comment-only lines.  If there are any such lines before the first section
    header, they're returned in a first ``section`` of ``None``.
    """
    section = None
    content = []
    for line in yield_lines(s):
        if line.startswith("["):
            if line.endswith("]"):
                if section or content:
                    yield section, content
                section = line[1:-1].strip()
                content = []
            else:
                raise ValueError("Invalid section heading", line)
        else:
            content.append(line)

    yield section, content

def safe_name(name):
    """Convert an arbitrary string to a standard distribution name

    Any runs of non-alphanumeric/. characters are replaced with a single '-'.
    """
    return re.sub('[^A-Za-z0-9.]+', '-', name)

def safe_extra(extra):
    """Convert an arbitrary string to a standard 'extra' name

    Any runs of non-alphanumeric characters are replaced with a single '_',
    and the result is always lowercased.
    """
    return re.sub('[^A-Za-z0-9.]+', '_', extra).lower()


