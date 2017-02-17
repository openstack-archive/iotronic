# -*- encoding: utf-8 -*-
#
# Copyright 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""
Base classes for storage engines
"""

import abc

from oslo_config import cfg
from oslo_db import api as db_api
import six

_BACKEND_MAPPING = {'sqlalchemy': 'iotronic.db.sqlalchemy.api'}
IMPL = db_api.DBAPI.from_config(cfg.CONF, backend_mapping=_BACKEND_MAPPING,
                                lazy=True)


def get_instance():
    """Return a DB API instance."""
    return IMPL


@six.add_metaclass(abc.ABCMeta)
class Connection(object):
    """Base class for storage system connections."""

    @abc.abstractmethod
    def __init__(self):
        """Constructor."""

    @abc.abstractmethod
    def get_nodeinfo_list(self, columns=None, filters=None, limit=None,
                          marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching nodes.

        Return a list of the specified columns for all nodes that match the
        specified filters.

        :param columns: List of column names to return.
                        Defaults to 'id' column when columns == None.
        :param filters: Filters to apply. Defaults to None.

                        :associated: True | False
                        :reserved: True | False
                        :maintenance: True | False
                        :provision_state: provision state of node
                        :provisioned_before:
                            nodes with provision_updated_at field before this
                            interval in seconds
        :param limit: Maximum number of nodes to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def get_node_list(self, filters=None, limit=None, marker=None,
                      sort_key=None, sort_dir=None):
        """Return a list of nodes.

        :param filters: Filters to apply. Defaults to None.

                        :associated: True | False
                        :reserved: True | False
                        :maintenance: True | False
                        :provision_state: provision state of node
                        :provisioned_before:
                            nodes with provision_updated_at field before this
                            interval in seconds
        :param limit: Maximum number of nodes to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        """

    @abc.abstractmethod
    def create_node(self, values):
        """Create a new node.

        :param values: A dict containing several items used to identify
                       and track the node, and several dicts which are passed
                       into the Drivers when managing this node. For example:

                       ::

                        {
                         'uuid': uuidutils.generate_uuid(),
                         'instance_uuid': None,
                         'power_state': states.POWER_OFF,
                         'provision_state': states.AVAILABLE,
                         'properties': { ... },
                         'extra': { ... },
                        }
        :returns: A node.
        """

    @abc.abstractmethod
    def get_node_by_id(self, node_id):
        """Return a node.

        :param node_id: The id of a node.
        :returns: A node.
        """

    @abc.abstractmethod
    def get_node_by_uuid(self, node_uuid):
        """Return a node.

        :param node_uuid: The uuid of a node.
        :returns: A node.
        """

    @abc.abstractmethod
    def get_node_by_name(self, node_name):
        """Return a node.

        :param node_name: The logical name of a node.
        :returns: A node.
        """

    @abc.abstractmethod
    def get_node_by_code(self, instance):
        """Return a node.

        :param instance: The instance code or uuid to search for.
        :returns: A node.
        """

    @abc.abstractmethod
    def destroy_node(self, node_id):
        """Destroy a node and all associated interfaces.

        :param node_id: The id or uuid of a node.
        """

    @abc.abstractmethod
    def update_node(self, node_id, values):
        """Update properties of a node.

        :param node_id: The id or uuid of a node.
        :param values: Dict of values to update.
        :returns: A node.
        :raises: NodeAssociated
        :raises: NodeNotFound
        """

    @abc.abstractmethod
    def get_conductor(self, hostname):
        """Retrieve a conductor's service record from the database.

        :param hostname: The hostname of the conductor service.
        :returns: A conductor.
        :raises: ConductorNotFound
        """

    @abc.abstractmethod
    def unregister_conductor(self, hostname):
        """Remove this conductor from the service registry immediately.

        :param hostname: The hostname of this conductor service.
        :raises: ConductorNotFound
        """

    @abc.abstractmethod
    def touch_conductor(self, hostname):
        """Mark a conductor as active by updating its 'updated_at' property.

        :param hostname: The hostname of this conductor service.
        :raises: ConductorNotFound
        """

    @abc.abstractmethod
    def create_session(self, values):
        """Create a new location.

        :param values: session_id.
        """

    @abc.abstractmethod
    def update_session(self, session_id, values):
        """Update properties of an session.

        :param session_id: The id of a session.
        :param values: Dict of values to update.
        :returns: A session.
        """

    @abc.abstractmethod
    def create_location(self, values):
        """Create a new location.

        :param values: Dict of values.
        """

    @abc.abstractmethod
    def update_location(self, location_id, values):
        """Update properties of an location.

        :param location_id: The id of a location.
        :param values: Dict of values to update.
        :returns: A location.
        """

    @abc.abstractmethod
    def destroy_location(self, location_id):
        """Destroy an location.

        :param location_id: The id or MAC of a location.
        """

    @abc.abstractmethod
    def get_locations_by_node_id(self, node_id, limit=None, marker=None,
                                 sort_key=None, sort_dir=None):
        """List all the locations for a given node.

        :param node_id: The integer node ID.
        :param limit: Maximum number of locations to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted
        :param sort_dir: direction in which results should be sorted
                         (asc, desc)
        :returns: A list of locations.
        """

    @abc.abstractmethod
    def get_wampagent(self, hostname):
        """Retrieve a wampagent's service record from the database.

        :param hostname: The hostname of the wampagent service.
        :returns: A wampagent.
        :raises: WampAgentNotFound
        """

    @abc.abstractmethod
    def get_registration_wampagent(self):
        """Retrieve the registration wampagent record from the database.

        :returns: A wampagent.
        :raises: WampAgentNotFound
        """

    @abc.abstractmethod
    def unregister_wampagent(self, hostname):
        """Remove this wampagent from the service registry immediately.

        :param hostname: The hostname of this wampagent service.
        :raises: WampAgentNotFound
        """

    @abc.abstractmethod
    def touch_wampagent(self, hostname):
        """Mark a wampagent as active by updating its 'updated_at' property.

        :param hostname: The hostname of this wampagent service.
        :raises: WampAgentNotFound
        """

    @abc.abstractmethod
    def get_wampagent_list(self, filters=None, limit=None, marker=None,
                           sort_key=None, sort_dir=None):
        """Return a list of wampagents.

        :param filters: Filters to apply. Defaults to None.
        :param limit: Maximum number of wampagents to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        """

    @abc.abstractmethod
    def get_session_by_node_uuid(self, filters=None, limit=None, marker=None,
                           sort_key=None, sort_dir=None):
        """Return a Wamp session of a Node

        :param filters: Filters to apply. Defaults to None.
        :param limit: Maximum number of wampagents to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        """
