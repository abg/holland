"""Exceptions raise by holland.core"""

class HollandError(Exception):
    """Base Holland Error"""

class BackupError(HollandError):
    """General Backup failure"""
    pass

class ConfigError(HollandError):
    """Configuration error"""

class InsufficientSpaceError(HollandError):
    """Operation could not complete due to disk space"""

class ArgumentError(HollandError):
    """Invalid argument"""
