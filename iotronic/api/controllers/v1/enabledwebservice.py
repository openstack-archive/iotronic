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
from iotronic.api.controllers import link
from iotronic.api.controllers.v1 import collection
from iotronic.api.controllers.v1 import types
from iotronic.api.controllers.v1 import utils as api_utils
from iotronic.api import expose
from iotronic.common import exception
from iotronic.common import policy
from iotronic import objects

import pecan
from pecan import rest
import wsme
from wsme import types as wtypes

_DEFAULT_RETURN_FIELDS = ('board_uuid', 'http_port', 'https_port',
                          'dns', 'zone', 'extra')


class EnabledWebservice(base.APIBase):
    """API representation of a enabled_webservice.

    """
    http_port = wsme.types.IntegerType()
    https_port = wsme.types.IntegerType()
    board_uuid = types.uuid
    dns = wsme.wsattr(wtypes.text)
    zone = wsme.wsattr(wtypes.text)
    extra = types.jsontype

    links = wsme.wsattr([link.Link], readonly=True)

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.EnabledWebservice.fields)
        for k in fields:
            # Skip fields we do not expose.
            if not hasattr(self, k):
                continue
            self.fields.append(k)
            setattr(self, k, kwargs.get(k, wtypes.Unset))

    @staticmethod
    def _convert(enabled_webservice, fields=None):
        if fields is not None:
            enabled_webservice.unset_fields_except(fields)

        return enabled_webservice

    @classmethod
    def convert_with_links(cls, rpc_enabled_webservice, fields=None):
        enabled_webservice = EnabledWebservice(
            **rpc_enabled_webservice.as_dict())
        if fields is not None:
            api_utils.check_for_invalid_fields(fields,
                                               enabled_webservice.as_dict())

        return cls._convert(enabled_webservice,
                            fields=fields)


class EnabledWebserviceCollection(collection.Collection):
    """API representation of a collection of EnabledWebservices."""

    EnabledWebservices = [EnabledWebservice]
    """A list containing EnabledWebservices objects"""

    def __init__(self, **kwargs):
        self._type = 'EnabledWebservices'

    @staticmethod
    def convert_with_links(EnabledWebservices, limit, url=None, fields=None,
                           **kwargs):
        collection = EnabledWebserviceCollection()
        collection.EnabledWebservices = [
            EnabledWebservice.convert_with_links(n, fields=fields)
            for n in EnabledWebservices]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class EnabledWebservicesController(rest.RestController):
    """REST controller for EnabledWebservices."""

    invalid_sort_key_list = ['extra', ]

    def _get_EnabledWebservices_collection(self, marker, limit,
                                           sort_key, sort_dir, project_id,
                                           fields=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.EnabledWebservice.get_by_id(
                pecan.request.context,
                marker)

        if sort_key in self.invalid_sort_key_list:
            raise exception.InvalidParameterValue(
                ("The sort_key value %(key)s is an invalid field for "
                 "sorting") % {'key': sort_key})

        filters = {}
        filters['project_id'] = project_id

        EnabledWebservices = objects.EnabledWebservice.list(
            pecan.request.context, limit,
            marker_obj,
            sort_key=sort_key,
            sort_dir=sort_dir,
            filters=filters)

        parameters = {'sort_key': sort_key, 'sort_dir': sort_dir}

        return EnabledWebserviceCollection.convert_with_links(
            EnabledWebservices, limit,
            fields=fields,
            **parameters)

    @expose.expose(EnabledWebserviceCollection, types.uuid, int, wtypes.text,
                   wtypes.text, types.listtype)
    def get_all(self, marker=None,
                limit=None, sort_key='id', sort_dir='asc',
                fields=None):
        """Retrieve a list of EnabledWebservices.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
                      This value cannot be larger than the value of max_limit
                      in the [api] section of the ironic configuration, or only
                      max_limit resources will be returned.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """
        cdict = pecan.request.context.to_policy_values()
        policy.authorize('iot:enabledwebservice:get', cdict, cdict)
        project_id = pecan.request.context.project_id

        if fields is None:
            fields = _DEFAULT_RETURN_FIELDS
        return self._get_EnabledWebservices_collection(marker,
                                                       limit,
                                                       sort_key, sort_dir,
                                                       project_id=project_id,
                                                       fields=fields)
