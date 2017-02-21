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


class Plugin(base.IotronicObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = db_api.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'name': obj_utils.str_or_none,
        'config': obj_utils.str_or_none,
        'extra': obj_utils.dict_or_none,
    }

    @staticmethod
    def _from_db_object(plugin, db_plugin):
        """Converts a database entity to a formal object."""
        for field in plugin.fields:
            plugin[field] = db_plugin[field]
        plugin.obj_reset_changes()
        return plugin

    @base.remotable_classmethod
    def get(cls, context, plugin_id):
        """Find a plugin based on its id or uuid and return a Node object.

        :param plugin_id: the id *or* uuid of a plugin.
        :returns: a :class:`Node` object.
        """
        if strutils.is_int_like(plugin_id):
            return cls.get_by_id(context, plugin_id)
        elif uuidutils.is_uuid_like(plugin_id):
            return cls.get_by_uuid(context, plugin_id)
        else:
            raise exception.InvalidIdentity(identity=plugin_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, plugin_id):
        """Find a plugin based on its integer id and return a Node object.

        :param plugin_id: the id of a plugin.
        :returns: a :class:`Node` object.
        """
        db_plugin = cls.dbapi.get_plugin_by_id(plugin_id)
        plugin = Plugin._from_db_object(cls(context), db_plugin)
        return plugin

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a plugin based on uuid and return a Node object.

        :param uuid: the uuid of a plugin.
        :returns: a :class:`Node` object.
        """
        db_plugin = cls.dbapi.get_plugin_by_uuid(uuid)
        plugin = Plugin._from_db_object(cls(context), db_plugin)
        return plugin

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a plugin based on name and return a Node object.

        :param name: the logical name of a plugin.
        :returns: a :class:`Node` object.
        """
        db_plugin = cls.dbapi.get_plugin_by_name(name)
        plugin = Plugin._from_db_object(cls(context), db_plugin)
        return plugin

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None, sort_key=None,
             sort_dir=None, filters=None):
        """Return a list of Plugin objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: Filters to apply.
        :returns: a list of :class:`Plugin` object.

        """
        db_plugins = cls.dbapi.get_plugin_list(filters=filters,
                                               limit=limit,
                                               marker=marker,
                                               sort_key=sort_key,
                                               sort_dir=sort_dir)
        return [Plugin._from_db_object(cls(context), obj)
                for obj in db_plugins]

    @base.remotable
    def create(self, context=None):
        """Create a Plugin record in the DB.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        plugin before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Plugin(context)

        """
        values = self.obj_get_changes()
        db_plugin = self.dbapi.create_plugin(values)
        self._from_db_object(self, db_plugin)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Plugin from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Plugin(context)
        """
        self.dbapi.destroy_plugin(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Plugin.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        plugin before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Plugin(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_plugin(self.uuid, updates)
        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Refresh the object by re-fetching from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Plugin(context)
        """
        current = self.__class__.get_by_uuid(self._context, self.uuid)
        for field in self.fields:
            if (hasattr(
                    self, base.get_attrname(field)) and
                    self[field] != current[field]):
                self[field] = current[field]
