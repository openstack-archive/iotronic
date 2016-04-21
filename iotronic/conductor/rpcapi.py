# coding=utf-8

# Copyright 2013 Hewlett-Packard Development Company, L.P.
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
"""
Client side of the conductor RPC API.
"""

import oslo_messaging as messaging

from iotronic.common import hash_ring
from iotronic.common import rpc
from iotronic.conductor import manager
from iotronic.objects import base as objects_base

from oslo_log import log as logging
LOG = logging.getLogger('object')


class ConductorAPI(object):
    """Client side of the conductor RPC API.

    API version history:
    |    1.0 - Initial version.
    """

    # NOTE(rloo): This must be in sync with manager.ConductorManager's.
    RPC_API_VERSION = '1.0'

    def __init__(self, topic=None):
        super(ConductorAPI, self).__init__()
        self.topic = topic
        if self.topic is None:
            self.topic = manager.MANAGER_TOPIC

        target = messaging.Target(topic=self.topic,
                                  version='1.0')
        serializer = objects_base.IotronicObjectSerializer()
        self.client = rpc.get_client(target,
                                     version_cap=self.RPC_API_VERSION,
                                     serializer=serializer)
        # NOTE(deva): this is going to be buggy
        self.ring_manager = hash_ring.HashRingManager()

    def update_node(self, context, node_obj, topic=None):
        """Synchronously, have a conductor update the node's information.

        Update the node's information in the database and return a node object.
        The conductor will lock the node while it validates the supplied
        information. If driver_info is passed, it will be validated by
        the core drivers. If instance_uuid is passed, it will be set or unset
        only if the node is properly configured.

        Note that power_state should not be passed via this method.
        Use change_node_power_state for initiating driver actions.

        :param context: request context.
        :param node_obj: a changed (but not saved) node object.
        :param topic: RPC topic. Defaults to self.topic.
        :returns: updated node object, including all fields.

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.1')
        return cctxt.call(context, 'update_node', node_obj=node_obj)

    def destroy_node(self, context, node_id, topic=None):
        """Delete a node.

        :param context: request context.
        :param node_id: node id or uuid.
        :raises: NodeLocked if node is locked by another conductor.
        :raises: NodeAssociated if the node contains an instance
            associated with it.
        :raises: InvalidState if the node is in the wrong provision
            state to perform deletion.
        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'destroy_node', node_id=node_id)
