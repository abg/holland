"""Reads package entry points
"""
import os, sys
from zipimport import zipimporter, ZipImportError
from StringIO import StringIO
from itertools import chain

from extensions.entry_point import EntryPoint
from extensions.registry import stream_registered
from extensions.plugin import Plugin

try:
    from distutils2._backport.pkgutil import get_distributions
    HAS_DISTUTILS2 = True
except ImportError:
    HAS_DISTUTILS2 = False

def _open_egg_info_file(path, filename):
    """Returns the EGG-INFO directory"""
    extension = os.path.splitext(path)[-1].lower()
    is_dir = os.path.isdir(path)

    if (extension == '.egg-info' or extension == '.dist-info') and is_dir:
        path = os.path.join(path, filename)
        if os.path.exists(path):
            return open(path)
    elif extension == '.egg':
        if is_dir:
            path = os.path.join(path, 'EGG-INFO', filename)
            if os.path.exists(path):
                return open(path)
        else:
            # let's see if it's a zipped egg
            try:
                archive = zipimporter(path)
                path = archive.get_data('EGG-INFO/%s' % filename)
                return StringIO(path)
            except (ZipImportError, IOError):
                # happens if it's not a zip file
                # or if it doesn't contain an EGG-INFO/filename file
                return None
    return None

def _ep_map(path, consume_entry_points=False):
    """Returns an EntryPoint map."""
    if consume_entry_points and not path.endswith('.dist-info'):
        entry_points = _open_egg_info_file(path, 'entry_points.txt')
        if entry_points is not None:
            return EntryPoint.parse_map(entry_points)
    entry_points = _open_egg_info_file(path, 'PLUGINS')
    if entry_points is not None:
        return EntryPoint.parse_map(entry_points)

def _yield_ep(ep_map, group, name):
    """Filtering entry point by group and name."""
    for ep_group in ep_map:
        if ep_group != group and group is not None:
            continue
        for ep_name in ep_map[ep_group]:
            if ep_name != name and name is not None:
                continue
            ep = ep_map[ep_group][ep_name]
            yield Plugin(ep, ep_group, ep_name)

def get_plugins(group=None, name=None, consume_entry_points=False,
                paths=sys.path):
    """Returns entry points."""
    yielders = []

    # dynamic entry points
    dynamic_entry_points = stream_registered()
    if dynamic_entry_points != '':
        ep_map = EntryPoint.parse_map(StringIO(dynamic_entry_points))
        if ep_map is not None:
            yielders.append(_yield_ep(ep_map, group, name))

    # installed entry points
    for path in paths:
        if not os.path.exists(path):
            continue

        if os.path.isfile(path):
            ep_map = _ep_map(path, consume_entry_points)
            if ep_map is not None:
                yielders.append(_yield_ep(ep_map, group, name))

        elif os.path.isdir(path):
            for entry in os.listdir(path):
                fullpath = os.path.join(path, entry)
                ep_map = _ep_map(fullpath, consume_entry_points)
                if ep_map is not None:
                    yielders.append(_yield_ep(ep_map, group, name))

    return chain(*yielders)

