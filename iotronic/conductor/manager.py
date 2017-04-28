# coding=utf-8

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

from iotronic.common import exception
from iotronic.common.i18n import _LI
from iotronic.common.i18n import _LW
from iotronic.conductor import endpoints as endp
from iotronic.db import api as dbapi
import os
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
from oslo_messaging.rpc import dispatcher
import signal
import time

LOG = logging.getLogger(__name__)

MANAGER_TOPIC = 'iotronic.conductor_manager'
RAGENT = None

conductor_opts = [
    cfg.StrOpt('api_url',
               help='URL of Iotronic API service. If not set iotronic can '
                    'get the current value from the keystone service '
                    'catalog.'),
    cfg.IntOpt('heartbeat_timeout',
               default=60,
               help='Maximum time (in seconds) since the last check-in '
                    'of a conductor. A conductor is considered inactive '
                    'when this time has been exceeded.'),
]

CONF = cfg.CONF
CONF.register_opts(conductor_opts, 'conductor')


class ConductorManager(object):
    RPC_API_VERSION = '1.0'

    def __init__(self, host):
        logging.register_options(CONF)
        CONF(project='iotronic')
        logging.setup(CONF, "iotronic-conductor")

        signal.signal(signal.SIGINT, self.stop_handler)

        if not host:
            host = CONF.host
        self.host = host
        self.topic = MANAGER_TOPIC
        self.dbapi = dbapi.get_instance()

        try:
            cdr = self.dbapi.register_conductor(
                {'hostname': self.host})
        except exception.ConductorAlreadyRegistered:
            LOG.warn(_LW("A conductor with hostname %(hostname)s "
                         "was previously registered. Updating registration"),
                     {'hostname': self.host})

            cdr = self.dbapi.register_conductor({'hostname': self.host},
                                                update_existing=True)
        self.conductor = cdr

        transport = oslo_messaging.get_transport(cfg.CONF)
        target = oslo_messaging.Target(topic=self.topic, server=self.host,
                                       version=self.RPC_API_VERSION)

        ragent = self.dbapi.get_registration_wampagent()

        LOG.info("Found registration agent: %s on %s",
                 ragent.hostname, ragent.wsurl)

        endpoints = [
            endp.ConductorEndpoint(ragent),
        ]
        access_policy = dispatcher.DefaultRPCAccessPolicy
        self.server = oslo_messaging.get_rpc_server(
            transport, target,
            endpoints, executor='threading',
            access_policy=access_policy)

        self.server.start()

        while True:
            time.sleep(1)

    def stop_handler(self, signum, frame):
        LOG.info("Stopping server")
        self.server.stop()
        self.server.wait()
        self.del_host()
        os._exit(0)

    def del_host(self, deregister=True):
        if deregister:
            try:
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
