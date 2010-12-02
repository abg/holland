"""Plugin API"""

from holland.core.plugin.base import *
from holland.core.plugin.manager import EntrypointPluginManager

manager = EntrypointPluginManager()
register = manager.register
