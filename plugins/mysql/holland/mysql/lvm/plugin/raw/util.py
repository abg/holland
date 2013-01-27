"""Utility functions to help out the mysql-lvm plugin"""
import os
import shutil
import tempfile
import logging
from holland.core import open_stream
from holland.mysql.lvm.actions import FlushAndLockMySQLAction, \
                                             RecordMySQLReplicationAction, \
                                             InnodbRecoveryAction, \
                                             TarArchiveAction
from holland.mysql.lvm.plugin.common import log_final_snapshot_size

LOG = logging.getLogger(__name__)

def setup_actions(snapshot, config, client, snap_datadir, spooldir):
    """Setup actions for a LVM snapshot based on the provided
    configuration.

    Optional actions:
        * MySQL locking
        * InnoDB recovery
        * Recording MySQL replication
    """
    if config['mysql-lvm']['lock-tables']:
        extra_flush = config['mysql-lvm']['extra-flush-tables']
        act = FlushAndLockMySQLAction(client, extra_flush)
        snapshot.register('pre-snapshot', act, priority=100)
        snapshot.register('post-snapshot', act, priority=100)
    if config['mysql-lvm'].get('replication', True):
        repl_cfg = config.setdefault('mysql:replication', {})
        act = RecordMySQLReplicationAction(client, repl_cfg)
        snapshot.register('pre-snapshot', act, 0)
    if config['mysql-lvm']['innodb-recovery']:
        mysqld_config = dict(config['mysqld'])
        mysqld_config['datadir'] = snap_datadir
        if not mysqld_config['tmpdir']:
            mysqld_config['tmpdir'] = tempfile.gettempdir()
        ib_log_size = client.show_variable('innodb_log_file_size')
        mysqld_config['innodb-log-file-size'] = ib_log_size
        act = InnodbRecoveryAction(mysqld_config)
        snapshot.register('post-mount', act, priority=100)


    archive_stream = open_stream(os.path.join(spooldir, 'backup.tar'),
                                 'w',
                                 **config['compression'])
    act = TarArchiveAction(snap_datadir, archive_stream, config['tar'])
    snapshot.register('post-mount', act, priority=50)

    snapshot.register('pre-remove', log_final_snapshot_size)
