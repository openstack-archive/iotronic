#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.


from iotronic.api.controllers import base
from iotronic.api.controllers.v1 import collection
from iotronic.api.controllers.v1 import types
from iotronic.api.controllers.v1 import utils as api_utils
from iotronic.api import expose
from iotronic.common import exception
from iotronic import objects
import pecan
from pecan import rest
import wsme
from wsme import types as wtypes


class Plugin(base.APIBase):
    """API representation of a plugin.

    """

    uuid = types.uuid
    name = wsme.wsattr(wtypes.text)
    config = wsme.wsattr(wtypes.text)
    extra = types.jsontype

    @staticmethod
    def _convert(plugin, url, expand=True, show_password=True):
        if not expand:
            except_list = ['name', 'code', 'status', 'uuid', 'session', 'type']
            plugin.unset_fields_except(except_list)
            return plugin
        return plugin

    @classmethod
    def convert(cls, rpc_plugin, expand=True):
        plugin = Plugin(**rpc_plugin.as_dict())
        # plugin.id = rpc_plugin.id
        return cls._convert(plugin, pecan.request.host_url,
                            expand,
                            pecan.request.context.show_password)

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Plugin.fields)
        for k in fields:
            # Skip fields we do not expose.
            if not hasattr(self, k):
                continue
            self.fields.append(k)
            setattr(self, k, kwargs.get(k, wtypes.Unset))


class PluginCollection(collection.Collection):
    """API representation of a collection of plugins."""

    plugins = [Plugin]
    """A list containing plugins objects"""

    def __init__(self, **kwargs):
        self._type = 'plugins'

    @staticmethod
    def convert(plugins, limit, url=None, expand=False, **kwargs):
        collection = PluginCollection()
        collection.plugins = [
            Plugin.convert(
                n, expand) for n in plugins]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class PluginsController(rest.RestController):
    invalid_sort_key_list = []

    def _get_plugins_collection(self, marker, limit, sort_key, sort_dir,
                                expand=False, resource_url=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Plugin.get_by_uuid(pecan.request.context,
                                                    marker)

        if sort_key in self.invalid_sort_key_list:
            raise exception.InvalidParameterValue(
                ("The sort_key value %(key)s is an invalid field for "
                 "sorting") % {'key': sort_key})

        filters = {}
        plugins = objects.Plugin.list(pecan.request.context, limit, marker_obj,
                                      sort_key=sort_key, sort_dir=sort_dir,
                                      filters=filters)

        parameters = {'sort_key': sort_key, 'sort_dir': sort_dir}
        return PluginCollection.convert(plugins, limit,
                                        url=resource_url,
                                        expand=expand,
                                        **parameters)

    @expose.expose(PluginCollection, types.uuid, int, wtypes.text, wtypes.text)
    def get_all(self, marker=None, limit=None, sort_key='id',
                sort_dir='asc'):
        """Retrieve a list of plugins.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        return self._get_plugins_collection(marker,
                                            limit, sort_key, sort_dir)

    @expose.expose(Plugin, types.uuid_or_name)
    def get(self, plugin_ident):
        """Retrieve information about the given plugin.

        :param plugin_ident: UUID or logical name of a plugin.
        """
        rpc_plugin = api_utils.get_rpc_plugin(plugin_ident)
        plugin = Plugin(**rpc_plugin.as_dict())
        plugin.id = rpc_plugin.id
        return Plugin.convert(plugin)

    @expose.expose(Plugin, body=Plugin, status_code=201)
    def post(self, Plugin):
        """Create a new Plugin.

        :param Plugin: a Plugin within the request body.
        """
        if not Plugin.name:
            raise exception.MissingParameterValue(
                ("Name is not specified."))

        if Plugin.name:
            if not api_utils.is_valid_name(Plugin.name):
                msg = ("Cannot create plugin with invalid name %(name)s")
                raise wsme.exc.ClientSideError(msg % {'name': Plugin.name},
                                               status_code=400)

        new_Plugin = objects.Plugin(pecan.request.context,
                                    **Plugin.as_dict())

        new_Plugin = pecan.request.rpcapi.create_plugin(pecan.request.context,
                                                        new_Plugin)
        return Plugin.convert(new_Plugin)

    @expose.expose(None, types.uuid_or_name, status_code=204)
    def delete(self, plugin_ident):
        """Delete a plugin.

        :param plugin_ident: UUID or logical name of a plugin.
        """
        rpc_plugin = api_utils.get_rpc_plugin(plugin_ident)
        pecan.request.rpcapi.destroy_plugin(pecan.request.context,
                                            rpc_plugin.uuid)
