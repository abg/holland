"""
Command support for generating backupset configs
"""

import os
import sys
import tempfile
import logging
import subprocess
from StringIO import StringIO

from holland.core.command import Command, option
from holland.core.plugin import load_first_entrypoint, PluginLoadError
from holland.core.config.configobj import ConfigObj, flatten_errors, ParseError
from holland.core.config import hollandcfg
from holland.core.config.validate import Validator
from holland.core.config.checks import validator

LOGGER = logging.getLogger(__name__)


def which(cmd, search_path=None):
    """Find the canonical path for a command"""
    if cmd == '':
        return None

    if not search_path:
        search_path = os.getenv('PATH', '').split(':')

    logging.debug("Using search_path: %r", search_path)
    for name in search_path:
        cmd_path = os.path.join(name, cmd)
        if os.access(cmd_path, os.X_OK):
            return cmd_path
    else:
        return None

def _find_editor():
    candidates = [
        os.getenv('VISUAL',''),
        os.getenv('EDITOR',''),
        '/usr/bin/editor',
        'vim',
        'vi',
        'ed'
    ]
    for command in candidates:
        real_cmd = which(command)
        logging.debug("%r => %r", command, real_cmd)
        if real_cmd:
            return real_cmd
    else:
        return None

def _report_errors(cfg, errors):
    for entry in flatten_errors(cfg, errors):
        (section,), key, error = entry
        param = '.'.join((section, key))
        if key is not None:
            pass
        else:
            param = ' '.join((section, '[missing section]'))
        if error == False:
            error = 'Missing value or section'
        print >>sys.stderr, param, ' = ', error

def confirm(prompt=None, resp=False):
    """prompts for yes or no response from the user. Returns True for yes and
    False for no.

    'resp' should be set to the default value assumed by the caller when
    user simply types ENTER.

    >>> confirm(prompt='Create Directory?', resp=True)
    Create Directory? [y]|n: 
    True
    >>> confirm(prompt='Create Directory?', resp=False)
    Create Directory? [n]|y: 
    False
    >>> confirm(prompt='Create Directory?', resp=False)
    Create Directory? [n]|y: y
    True

    """
    
    if prompt is None:
        prompt = 'Confirm'

    if resp:
        prompt = '%s ([%s] or %s): ' % (prompt, 'y', 'n')
    else:
        prompt = '%s ([%s] or %s): ' % (prompt, 'n', 'y')
        
    while True:
        ans = raw_input(prompt)
        if not ans:
            return resp
        if ans not in ['y', 'Y', 'n', 'N']:
            print >>sys.stderr, 'please enter y or n.'
            continue
        if ans == 'y' or ans == 'Y':
            return True
        if ans == 'n' or ans == 'N':
            return False

class MkConfig(Command):
    """${cmd_usage}

    Generate a config file for a backup 
    plugin.

    ${cmd_option_list}
        
    """

    name = 'mk-config'

    aliases = [
        'mc'
    ]

    options = [
        option('--name', 
                help='Name of the backupset'),
        option('--edit', action='store_true',
                help='Edit the generated config'),
        option('--provider', action='store_true',
                help='Generate a provider config'),
        option('--file', '-f',
                help='Save the final config to the specified file'),
    ]

    description = 'Generate a config file for a backup plugin'
    
    def _next_section_comments(self, section):
        main = section.parent
        if not main:
            # just in case we have any 'root level' items
            main = section.main

        idx = main.keys().index(section.name) + 1
        if idx >= len(main.keys()):
            return main.final_comment
        else:
            return main.comments[main.keys()[idx]]

    def _next_key_comments(self, section, key):
        idx = section.keys().index(key) + 1
        if idx >= len(section.keys()):
            return self._next_section_comments(section)
        else:
            return section.comments[section.keys()[idx]]

    def _filter_none(self, section, key, filter_list):
        if section[key] is None:
            comment_list = self._next_key_comments(section, key)
            comment_list.insert(0, '# %s = "" # no default' % key)
            filter_list.append((section, key))

    # After initial validation:
    #   run through and flag required parameters with a 'REQUIRED' comment
    #   run through and comment out default=None parameters
    def _cleanup_config(self, config):
        errors = config.validate(validator, preserve_errors=True,copy=True)
        # First flag any required parameters
        for entry in flatten_errors(config, errors):
            section_list, key, error = entry
            section_name, = section_list
            if error is False:
                config[section_name][key] = ''
                config[section_name].comments[key].append('REQUIRED')
            elif error:
                print >>sys.stderr, "Bad configspec generated error", error
        
        none_keys = []
        config.walk(self._filter_none, raise_errors=True, filter_list=none_keys)
        for sect, key in none_keys:
            if sect.comments.get(key):
                comment_list = self._next_key_comments(sect, key)
                map(lambda x: comment_list.insert(0, x), sect.comments[key])
            del sect[key]

    def run(self, cmd, opts, plugin_type):
        if opts.name and opts.provider:
            print >>sys.stderr, "Can't specify a name for a global provider config"
            return 1

        try:
            plugin_cls = load_first_entrypoint('holland.backup', plugin_type)
        except PluginLoadError, exc:
            logging.info("Failed to load backup plugin %r: %s",
                         plugin_type, exc)
            return 1
        
        try:
            cfgspec = sys.modules[plugin_cls.__module__].CONFIGSPEC
        except:
            print >>sys.stderr, "Could not load config-spec from plugin %r" % plugin_type
            return 1

        cfg = ConfigObj(configspec=cfgspec, list_values=True,stringify=True)
        if not opts.provider:
            # Add whitespace between [holland:backup] and the next section
            cfg['holland:backup'] = { 'plugin' : plugin_type, 
                                      'backups-to-keep' : 1,    # default keep 1 backup
                                      'estimated-size-factor' : 1.0  # default no size adjustment
                                    }
        self._cleanup_config(cfg)
        cfg.comments[cfg.keys()[0]].insert(0, '')
        cfg.initial_comment = []

        if opts.edit:
            done = False
            editor = _find_editor()
            if not editor:
                print >>sys.stderr, "Could not find a valid editor"
                return 1

            tmpfileobj = tempfile.NamedTemporaryFile()
            cfg.filename = tmpfileobj.name
            cfg.write()
            while not done:
                status = subprocess.call([editor, cfg.filename])
                if status != 0:
                    if not confirm("Editor exited with non-zero status[%d]. "
                                   "Would you like to retry?" % status):
                        print >>sys.stderr, "Aborting"
                        return 1
                    else:
                        continue
                try:
                    cfg.reload()
                except ParseError, exc:
                    print >>sys.stderr, "%s : %s" % \
                    (exc.msg, exc.line)
                else:
                    errors = cfg.validate(validator,preserve_errors=True)
                    if errors is True:
                        done = True
                        continue
                    else:
                        _report_errors(cfg, errors)

                if not confirm('There were configuration errors. Continue?'):
                    print >>sys.stderr, "Aborting"
                    return 1
            tmpfileobj.close()

        if not opts.name and not opts.file:
            cfg.write(sys.stdout)

        if opts.file:
            print >>sys.stderr, "Saving config to %r" % opts.file
            cfg.write(open(opts.file, 'w'))
        elif opts.name:
            base_dir = os.path.dirname(hollandcfg.filename)
            path = os.path.join(base_dir, 'backupsets', opts.name + '.conf')
            print >>sys.stderr, "Saving config to %r" % path
            cfg.write(open(path, 'w'))
        return 0
