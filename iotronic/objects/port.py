# coding=utf-8
#
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

from oslo_utils import strutils
from oslo_utils import uuidutils

from iotronic.common import exception
from iotronic.db import api as db_api
from iotronic.objects import base
from iotronic.objects import utils as obj_utils


class Port(base.IotronicObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = db_api.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'VIF_name': obj_utils.str_or_none,
        'network': obj_utils.str_or_none,
        'MAC_add': obj_utils.str_or_none,
        'ip': obj_utils.str_or_none,
        'board_uuid': obj_utils.str_or_none,
    }

    @staticmethod
    def _from_db_object(port, db_port):
        """Converts a database entity to a formal object."""
        for field in port.fields:
            port[field] = db_port[field]
        port.obj_reset_changes()
        return port

    @base.remotable_classmethod
    def get(cls, context, port_id):
        """Find a port based on its id or uuid and return a Port object.

        :param port_id: the id *or* uuid of a port.
        :returns: a :class:`Port` object.
        """
        if strutils.is_int_like(port_id):
            return cls.get_by_id(context, port_id)
        elif uuidutils.is_uuid_like(port_id):
            return cls.get_by_uuid(context, port_id)
        else:
            raise exception.InvalidIdentity(identity=port_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, port_id):
        """Find a port based on its integer id and return a Port object.

        :param port_id: the id of a port.
        :returns: a :class:`Port` object.
        """
        db_port = cls.dbapi.get_port_by_id(port_id)
        port = Port._from_db_object(cls(context), db_port)
        return port

    @base.remotable_classmethod
    def get_by_uuid(cls, context, port_uuid):
        """Find a port based on uuid and return a Port object.

        :param uuid: the uuid of a port.
        :returns: a :class:`Port` object.
        """
        db_port = cls.dbapi.get_port_by_uuid(port_uuid)
        port = Port._from_db_object(cls(context), db_port)
        return port

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a port based on name and return a Port object.

        :param name: the logical name of a port.
        :returns: a :class:`Port` object.
        """
        db_port = cls.dbapi.get_port_by_name(name)
        port = Port._from_db_object(cls(context), db_port)
        return port

    @base.remotable_classmethod
    def get_by_board_uuid(cls, context, board_uuid):
        """Return a list of port objects.

        :param context: Security context.
        :param board_uuid: The uuid of the board.

        """
        db_port = cls.dbapi.get_ports_by_board_uuid(board_uuid)
        return [Port._from_db_object(cls(context), obj)
                for obj in db_port]

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None, sort_key=None,
             sort_dir=None, filters=None):
        """Return a list of Port objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: Filters to apply.
        :returns: a list of :class:`Port` object.

        """
        db_ports = cls.dbapi.get_port_list(filters=filters,
                                           limit=limit,
                                           marker=marker,
                                           sort_key=sort_key,
                                           sort_dir=sort_dir)
        return [Port._from_db_object(cls(context), obj)
                for obj in db_ports]

    @base.remotable
    def create(self, context=None):
        """Create a Port record in the DB.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        service before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Port(context)

        """

        values = self.obj_get_changes()
        db_port = self.dbapi.create_port(values)
        self._from_db_object(self, db_port)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Port from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Port(context)
        """
        self.dbapi.destroy_port(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Port.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        service before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Port(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_port(self.uuid, updates)
        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Refresh the object by re-fetching from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Port(context)
        """
        current = self.__class__.get_by_uuid(self._context, self.uuid)
        for field in self.fields:
            if (hasattr(
                    self, base.get_attrname(field))
                    and self[field] != current[field]):
                self[field] = current[field]
