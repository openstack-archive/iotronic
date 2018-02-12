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


"""
ACTIONS = ['ServiceCall', 'ServiceStop', 'ServiceStart',
           'ServiceStatus', 'ServiceReboot']
CUSTOM_PARAMS = ['ServiceCall', 'ServiceStart', 'ServiceReboot']
NO_PARAMS = ['ServiceStatus']


def is_valid_action(action):
    if action not in ACTIONS:
        raise exception.InvalidServiceAction(action=action)
    return True


def want_customs_params(action):
    return True if action in CUSTOM_PARAMS else False


def want_params(action):
    return False if action in NO_PARAMS else True

"""

class Service(base.IotronicObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = db_api.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'name': obj_utils.str_or_none,
        'project': obj_utils.str_or_none,
        'port': int,
        'protocol': obj_utils.str_or_none,
        'extra': obj_utils.dict_or_none,
    }

    @staticmethod
    def _from_db_object(service, db_service):
        """Converts a database entity to a formal object."""
        for field in service.fields:
            service[field] = db_service[field]
        service.obj_reset_changes()
        return service

    @base.remotable_classmethod
    def get(cls, context, service_id):
        """Find a service based on its id or uuid and return a Board object.

        :param service_id: the id *or* uuid of a service.
        :returns: a :class:`Board` object.
        """
        if strutils.is_int_like(service_id):
            return cls.get_by_id(context, service_id)
        elif uuidutils.is_uuid_like(service_id):
            return cls.get_by_uuid(context, service_id)
        else:
            raise exception.InvalidIdentity(identity=service_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, service_id):
        """Find a service based on its integer id and return a Board object.

        :param service_id: the id of a service.
        :returns: a :class:`Board` object.
        """
        db_service = cls.dbapi.get_service_by_id(service_id)
        service = Service._from_db_object(cls(context), db_service)
        return service

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a service based on uuid and return a Board object.

        :param uuid: the uuid of a service.
        :returns: a :class:`Board` object.
        """
        db_service = cls.dbapi.get_service_by_uuid(uuid)
        service = Service._from_db_object(cls(context), db_service)
        return service

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a service based on name and return a Board object.

        :param name: the logical name of a service.
        :returns: a :class:`Board` object.
        """
        db_service = cls.dbapi.get_service_by_name(name)
        service = Service._from_db_object(cls(context), db_service)
        return service

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None, sort_key=None,
             sort_dir=None, filters=None):
        """Return a list of Service objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: Filters to apply.
        :returns: a list of :class:`Service` object.

        """
        db_services = cls.dbapi.get_service_list(filters=filters,
                                               limit=limit,
                                               marker=marker,
                                               sort_key=sort_key,
                                               sort_dir=sort_dir)
        return [Service._from_db_object(cls(context), obj)
                for obj in db_services]

    @base.remotable
    def create(self, context=None):
        """Create a Service record in the DB.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        service before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Service(context)

        """
        values = self.obj_get_changes()
        db_service = self.dbapi.create_service(values)
        self._from_db_object(self, db_service)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Service from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Service(context)
        """
        self.dbapi.destroy_service(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Service.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        service before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Service(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_service(self.uuid, updates)
        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Refresh the object by re-fetching from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Service(context)
        """
        current = self.__class__.get_by_uuid(self._context, self.uuid)
        for field in self.fields:
            if (hasattr(
                    self, base.get_attrname(field))
                    and self[field] != current[field]):
                        self[field] = current[field]
