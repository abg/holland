"""Plugin base classes"""

class BasePlugin(object):
    """Base plugin class from which all other plugins should derive"""

    def plugin_info(self):
        """Provide information about this plugin

        :returns: dict of key value pairs describing this plugin
        """
        raise NotImplementedError(
                'plugin_info() not implemented for this plugin'
              )

    def configure(self, config):
        """Configure this plugin

        :param config: a dict-like object with configuration options
        """
        raise NotImplementedError(
                'configure9) not implemented for this plugin'
              )

class BackupPlugin(BasePlugin):
    """Base class for Backup Plugins.

    Any plugin that provides a backup method should subclass ``BackupPlugin``
    """

    def __init__(self, name, spool):
        super(BackupPlugin, self).__init__()
        self.name = name
        self.spool = spool

    def setup(self):
        """Do additional setup for this plugin

        Called as part of the backup plugin's lifecycle
        """
        # default: noop

    #@property
    def configspec(self):
        """Provide a specification for the configurations this backup plugin
        accepts.
        """
        raise NotImplementedError(
                'configspec() not implemented by this backup plugin'
              )

    def configure(self, config):
        """Configure this plugin

        :param config: a dict-like object with configuration options
        """
        # default behavior, let the plugin validate its own config
        self.validate(config)

    def validate(self, config):
        """Validate a configuration

        :param config: a dict-like object to validate
        """
        raise NotImplementedError(
                'validate() not implemented by this backup plugin'
              )

    def dry_run(self, path_spec):
        """Run through the steps of the backup without actually performing the
        backup.

        This is dependent on the actual plugin implementation.  Implementations
        should avoid any heavy-lifting work that would negatively impact
        performance, but should generally try to log each step that would be
        done and make some determination if there is anything that would cause
        a real backup to fail if backup() had been run rather than dry_run()

        :param path_spec: a path spec where any backup data should be stored
        """
        raise NotImplementedError(
                'dry_run() not implemented by this backup plugin'
              )

    def backup(self, path_spec):
        """Perform a backup

        :param path_spec: path where backup data should be stored
        """
        raise NotImplementedError(
                'backup() not implemented by this backup plugin'
              )

    def teardown(self):
        """Perform any cleanup for this backup lifecycle"""
        # default: noop

    def cleanup(self, path_spec):
        """Cleanup a previous backup run

        This only needs to be implemented if additional cleanup beyond normal
        purging of data files needs to be done.  For instance, removing an old
        filesystem snapshot or releasing external resources.

        :param path_spec: path of a previous backup
        """
        # default: noop

