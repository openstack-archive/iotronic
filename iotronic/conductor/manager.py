# coding=utf-8

# Copyright 2013 Hewlett-Packard Development Company, L.P.
# Copyright 2013 International Business Machines Corporation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from eventlet import greenpool
import inspect

from iotronic.db import api as dbapi

from iotronic.common import exception

from iotronic.common.i18n import _LC
from iotronic.common.i18n import _LI
from iotronic.common.i18n import _LW

from iotronic.conductor import task_manager
from iotronic.wamp.rpcwamp import RPC_Wamp
from iotronic.wamp.wampresponse import WampResponse

from iotronic.openstack.common import periodic_task


from oslo_concurrency import lockutils
from oslo_config import cfg
from oslo_db import exception as db_exception
from oslo_log import log
import oslo_messaging as messaging
from oslo_utils import excutils

import threading

MANAGER_TOPIC = 'iotronic.conductor_manager'
WORKER_SPAWN_lOCK = "conductor_worker_spawn"

LOG = log.getLogger(__name__)

conductor_opts = [
    cfg.StrOpt('api_url',
               help=('URL of Iotronic API service. If not set iotronic can '
                     'get the current value from the keystone service '
                     'catalog.')),
    cfg.IntOpt('heartbeat_interval',
               default=10,
               help='Seconds between conductor heart beats.'),
    cfg.IntOpt('heartbeat_timeout',
               default=60,
               help='Maximum time (in seconds) since the last check-in '
                    'of a conductor. A conductor is considered inactive '
                    'when this time has been exceeded.'),
    cfg.IntOpt('periodic_max_workers',
               default=8,
               help='Maximum number of worker threads that can be started '
                    'simultaneously by a periodic task. Should be less '
                    'than RPC thread pool size.'),
    cfg.IntOpt('workers_pool_size',
               default=100,
               help='The size of the workers greenthread pool.'),
    cfg.IntOpt('node_locked_retry_attempts',
               default=3,
               help='Number of attempts to grab a node lock.'),
    cfg.IntOpt('node_locked_retry_interval',
               default=1,
               help='Seconds to sleep between node lock attempts.'),
    cfg.BoolOpt('send_sensor_data',
                default=False,
                help='Enable sending sensor data message via the '
                     'notification bus'),
    cfg.IntOpt('send_sensor_data_interval',
               default=600,
               help='Seconds between conductor sending sensor data message'
                    ' to ceilometer via the notification bus.'),
    cfg.ListOpt('send_sensor_data_types',
                default=['ALL'],
                help='List of comma separated meter types which need to be'
                     ' sent to Ceilometer. The default value, "ALL", is a '
                     'special value meaning send all the sensor data.'),
    cfg.IntOpt('sync_local_state_interval',
               default=180,
               help='When conductors join or leave the cluster, existing '
                    'conductors may need to update any persistent '
                    'local state as nodes are moved around the cluster. '
                    'This option controls how often, in seconds, each '
                    'conductor will check for nodes that it should '
                    '"take over". Set it to a negative value to disable '
                    'the check entirely.'),
    cfg.BoolOpt('configdrive_use_swift',
                default=False,
                help='Whether to upload the config drive to Swift.'),
    cfg.IntOpt('inspect_timeout',
               default=1800,
               help='Timeout (seconds) for waiting for node inspection. '
                    '0 - unlimited.'),
]
CONF = cfg.CONF
CONF.register_opts(conductor_opts, 'conductor')


class ConductorManager(periodic_task.PeriodicTasks):
    """Iotronic Conductor manager main class."""

    # sync with rpcapi.ConductorAPI's.
    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    def __init__(self, host, topic):
        super(ConductorManager, self).__init__()
        if not host:
            host = CONF.host
        self.host = host
        self.topic = topic
        self.wamp = RPC_Wamp()

    def init_host(self):
        self.dbapi = dbapi.get_instance()

        self._keepalive_evt = threading.Event()
        """Event for the keepalive thread."""

        self._worker_pool = greenpool.GreenPool(
            size=CONF.conductor.workers_pool_size)
        """GreenPool of background workers for performing tasks async."""

        try:
            # Register this conductor with the cluster
            cdr = self.dbapi.register_conductor(
                {'hostname': self.host})
        except exception.ConductorAlreadyRegistered:
            LOG.warn(_LW("A conductor with hostname %(hostname)s "
                         "was previously registered. Updating registration"),
                     {'hostname': self.host})

            cdr = self.dbapi.register_conductor({'hostname': self.host},
                                                update_existing=True)
        self.conductor = cdr

        # Spawn a dedicated greenthread for the keepalive
        try:
            self._spawn_worker(self._conductor_service_record_keepalive)
            LOG.info(_LI('Successfully started conductor with hostname '
                         '%(hostname)s.'),
                     {'hostname': self.host})
        except exception.NoFreeConductorWorker:
            with excutils.save_and_reraise_exception():
                LOG.critical(_LC('Failed to start keepalive'))
                self.del_host()

    def _collect_periodic_tasks(self, obj):
        for n, method in inspect.getmembers(obj, inspect.ismethod):
            if getattr(method, '_periodic_enabled', False):
                self.add_periodic_task(method)

    def del_host(self, deregister=True):
        self._keepalive_evt.set()
        if deregister:
            try:
                # Inform the cluster that this conductor is shutting down.
                # Note that rebalancing will not occur immediately, but when
                # the periodic sync takes place.
                self.dbapi.unregister_conductor(self.host)
                LOG.info(_LI('Successfully stopped conductor with hostname '
                             '%(hostname)s.'),
                         {'hostname': self.host})
            except exception.ConductorNotFound:
                pass
        else:
            LOG.info(_LI('Not deregistering conductor with hostname '
                         '%(hostname)s.'),
                     {'hostname': self.host})
        # Waiting here to give workers the chance to finish. This has the
        # benefit of releasing locks workers placed on nodes, as well as
        # having work complete normally.
        self._worker_pool.waitall()

    def periodic_tasks(self, context, raise_on_error=False):
        """Periodic tasks are run at pre-specified interval."""
        return self.run_periodic_tasks(context, raise_on_error=raise_on_error)

    @lockutils.synchronized(WORKER_SPAWN_lOCK, 'iotronic-')
    def _spawn_worker(self, func, *args, **kwargs):
        """Create a greenthread to run func(*args, **kwargs).

        Spawns a greenthread if there are free slots in pool, otherwise raises
        exception. Execution control returns immediately to the caller.

        :returns: GreenThread object.
        :raises: NoFreeConductorWorker if worker pool is currently full.

        """
        if self._worker_pool.free():
            return self._worker_pool.spawn(func, *args, **kwargs)
        else:
            raise exception.NoFreeConductorWorker()

    def _conductor_service_record_keepalive(self):
        while not self._keepalive_evt.is_set():
            try:
                self.dbapi.touch_conductor(self.host)
            except db_exception.DBConnectionError:
                LOG.warning(_LW('Conductor could not connect to database '
                                'while heartbeating.'))
            self._keepalive_evt.wait(CONF.conductor.heartbeat_interval)

    @messaging.expected_exceptions(exception.InvalidParameterValue,
                                   exception.MissingParameterValue,
                                   exception.NodeLocked)
    def update_node(self, context, node_obj):
        """Update a node with the supplied data.

        This method is the main "hub" for PUT and PATCH requests in the API.

        :param context: an admin context
        :param node_obj: a changed (but not saved) node object.

        """
        node_id = node_obj.uuid
        LOG.debug("RPC update_node called for node %s." % node_id)

        # NOTE(jroll) clear maintenance_reason if node.update sets
        # maintenance to False for backwards compatibility, for tools
        # not using the maintenance endpoint.
        delta = node_obj.obj_what_changed()

        with task_manager.acquire(context, node_id, shared=False):
            node_obj.save()

        return node_obj

    @messaging.expected_exceptions(exception.NodeLocked,
                                   exception.NodeNotConnected)
    def destroy_node(self, context, node_id):
        """Delete a node.

        :param context: request context.
        :param node_id: node id or uuid.
        :raises: NodeLocked if node is locked by another conductor.
        :raises: NodeNotConnected if the node is not connected.

        """

        with task_manager.acquire(context, node_id) as task:
            node = task.node
            r = WampResponse()
            r.clearConfig()
            response = self.wamp.rpc_call(
                'stack4things.' + node.uuid + '.configure',
                r.getResponse())
            if response['result'] == 0:
                node.destroy()
                LOG.info(_LI('Successfully deleted node %(node)s.'),
                         {'node': node.uuid})
            else:
                raise exception.NodeNotConnected(node=node.uuid)
