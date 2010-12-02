"""Managers for providing an interface to loading plugins"""

from holland.core.plugin.extensions import get, register

class PluginManager(object):
    def load(self, plugin_spec):
        """Load a plugin from a spec string

        :param plugin_spec: string describing where to load the plugin from
        :returns: plugin object
        """
        raise NotImplementedError("load() must be overridden in a subclass")

    def iterate(self, plugin_spec):
        """Iterate over plugins matching the plugin_spec

        :returns: iterable that yields plugin objects
        """
        raise NotImplementedError("iterate() must be overriden in a subclass")

class EntrypointPluginManager(PluginManager):
    """PluginManager that works with setuptools entry points or other plugins
    explicitly registered with the extensions framework
    """
    def load(self, plugin_spec):
        """Load a plugin from a spec string

        :param plugin_spec: string describing where to load the plugin from
        :returns: plugin object
        """
        group, name = plugin_spec.split(":", 1)
        for plugin in get(group=plugin_spec,
                          name=name,
                          consume_entry_points=True):
            return plugin.load()

    def iterate(self, plugin_spec=None):
        """Iterate over plugins matching the plugin_spec

        :returns: iterable that yields plugin objects
        """
        for plugin in get(group=plugin_spec, consume_entry_points=True):
            yield plugin.load()

    def register(self, group, name, location):
        """Register a new plugin with this manager"""
        # register from extensions
        register(group, name, location)
