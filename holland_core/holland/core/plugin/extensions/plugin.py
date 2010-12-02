# -*- coding: utf8 -*-
""" Plugin class
"""
class Plugin(object):
    """Plugin class"""
    def __init__(self, ep, group, name):
        self._ep = ep
        self.name = name
        self.group = group
        self.module_name = ep.module_name
        self.attrs = ep.attrs
        self.extras = ep.extras

    def __str__(self):
        s = "%s = %s" % (self.name, self.module_name)
        if self.attrs:
            s += ':' + '.'.join(self.attrs)
        if self.extras:
            s += ' [%s]' % ','.join(self.extras)
        return s

    def __repr__(self):
        return "Plugin(%r)" % str(self)

    def load(self):
        """Loads the registered object and returns it."""
        return self._ep.load()


