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

_DEFAULT_RETURN_FIELDS = ('name', 'uuid', 'project', 'port', 'protocol', 'extra')


class Service(base.APIBase):
    """API representation of a service.

    """
    uuid = types.uuid
    name = wsme.wsattr(wtypes.text)
    project = types.uuid
    port = wsme.types.IntegerType()
    protocol = wsme.wsattr(wtypes.text)
    extra = types.jsontype

    links = wsme.wsattr([link.Link], readonly=True)


    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Service.fields)
        for k in fields:
            # Skip fields we do not expose.
            if not hasattr(self, k):
                continue
            self.fields.append(k)
            setattr(self, k, kwargs.get(k, wtypes.Unset))

    @staticmethod
    def _convert_with_links(service, url, fields=None):
        service_uuid = service.uuid
        if fields is not None:
            service.unset_fields_except(fields)

        service.links = [link.Link.make_link('self', url, 'services',
                                            service_uuid),
                        link.Link.make_link('bookmark', url, 'services',
                                            service_uuid, bookmark=True)
                        ]
        return service

    @classmethod
    def convert_with_links(cls, rpc_service, fields=None):
        service = Service(**rpc_service.as_dict())

        if fields is not None:
            api_utils.check_for_invalid_fields(fields, service.as_dict())

        return cls._convert_with_links(service, pecan.request.public_url,
                                       fields=fields)


class ServiceCollection(collection.Collection):
    """API representation of a collection of services."""

    services = [Service]
    """A list containing services objects"""

    def __init__(self, **kwargs):
        self._type = 'services'

    @staticmethod
    def convert_with_links(services, limit, url=None, fields=None, **kwargs):
        collection = ServiceCollection()
        collection.services = [Service.convert_with_links(n, fields=fields)
                              for n in services]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class PublicServicesController(rest.RestController):
    """REST controller for Public Services."""

    invalid_sort_key_list = ['extra', 'location']

    def _get_services_collection(self, marker, limit,
                                sort_key, sort_dir,
                                fields=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Service.get_by_uuid(pecan.request.context,
                                                    marker)

        if sort_key in self.invalid_sort_key_list:
            raise exception.InvalidParameterValue(
                ("The sort_key value %(key)s is an invalid field for "
                 "sorting") % {'key': sort_key})

        filters = {}
        filters['public'] = True

        services = objects.Service.list(pecan.request.context, limit, marker_obj,
                                      sort_key=sort_key, sort_dir=sort_dir,
                                      filters=filters)

        parameters = {'sort_key': sort_key, 'sort_dir': sort_dir}

        return ServiceCollection.convert_with_links(services, limit,
                                                   fields=fields,
                                                   **parameters)

    @expose.expose(ServiceCollection, types.uuid, int, wtypes.text,
                   wtypes.text, types.listtype, types.boolean, types.boolean)
    def get_all(self, marker=None,
                limit=None, sort_key='id', sort_dir='asc',
                fields=None):
        """Retrieve a list of services.

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
        policy.authorize('iot:service:get', cdict, cdict)

        if fields is None:
            fields = _DEFAULT_RETURN_FIELDS
        return self._get_services_collection(marker,
                                            limit, sort_key, sort_dir,
                                            fields=fields)


class ServicesController(rest.RestController):
    """REST controller for Services."""

    public = PublicServicesController()

    invalid_sort_key_list = ['extra',]

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_services_collection(self, marker, limit,
                                sort_key, sort_dir,
                                fields=None, with_public=False,
                                all_services=False):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Service.get_by_uuid(pecan.request.context,
                                                    marker)

        if sort_key in self.invalid_sort_key_list:
            raise exception.InvalidParameterValue(
                ("The sort_key value %(key)s is an invalid field for "
                 "sorting") % {'key': sort_key})

        filters = {}
        if all_services and not pecan.request.context.is_admin:
            msg = ("all_services parameter can only be used  "
                   "by the administrator.")
            raise wsme.exc.ClientSideError(msg,
                                           status_code=400)
        else:
            if not all_services:
                filters['project'] = pecan.request.context.user_id
                if with_public:
                    filters['with_public'] = with_public

        services = objects.Service.list(pecan.request.context, limit, marker_obj,
                                      sort_key=sort_key, sort_dir=sort_dir,
                                      filters=filters)

        parameters = {'sort_key': sort_key, 'sort_dir': sort_dir}

        return ServiceCollection.convert_with_links(services, limit,
                                                   fields=fields,
                                                   **parameters)

    @expose.expose(Service, types.uuid_or_name, types.listtype)
    def get_one(self, service_ident, fields=None):
        """Retrieve information about the given service.

        :param service_ident: UUID or logical name of a service.
        :param fields: Optional, a list with a specified set of fields
            of the resource to be returned.
        """

        rpc_service = api_utils.get_rpc_service(service_ident)
        cdict = pecan.request.context.to_policy_values()
        cdict['project'] = rpc_service.project
        policy.authorize('iot:service:get_one', cdict, cdict)

        return Service.convert_with_links(rpc_service, fields=fields)

    @expose.expose(ServiceCollection, types.uuid, int, wtypes.text,
                   wtypes.text, types.listtype, types.boolean, types.boolean)
    def get_all(self, marker=None,
                limit=None, sort_key='id', sort_dir='asc',
                fields=None, with_public=False, all_services=False):
        """Retrieve a list of services.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
                      This value cannot be larger than the value of max_limit
                      in the [api] section of the ironic configuration, or only
                      max_limit resources will be returned.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param with_public: Optional boolean to get also public pluings.
        :param all_services: Optional boolean to get all the pluings.
                            Only for the admin
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """
        cdict = pecan.request.context.to_policy_values()
        policy.authorize('iot:service:get', cdict, cdict)

        if fields is None:
            fields = _DEFAULT_RETURN_FIELDS
        return self._get_services_collection(marker,
                                            limit, sort_key, sort_dir,
                                            with_public=with_public,
                                            all_services=all_services,
                                            fields=fields)

    @expose.expose(Service, body=Service, status_code=201)
    def post(self, Service):
        """Create a new Service.

        :param Service: a Service within the request body.
        """
        context = pecan.request.context
        cdict = context.to_policy_values()
        policy.authorize('iot:service:create', cdict, cdict)

        if not Service.name:
            raise exception.MissingParameterValue(
                ("Name is not specified."))

        if Service.name:
            if not api_utils.is_valid_name(Service.name):
                msg = ("Cannot create service with invalid name %(name)s")
                raise wsme.exc.ClientSideError(msg % {'name': Service.name},
                                               status_code=400)

        new_Service = objects.Service(pecan.request.context,
                                    **Service.as_dict())

        new_Service.project = cdict['project_id']
        new_Service = pecan.request.rpcapi.create_service(pecan.request.context,
                                                        new_Service)

        return Service.convert_with_links(new_Service)

    @expose.expose(None, types.uuid_or_name, status_code=204)
    def delete(self, service_ident):
        """Delete a service.

        :param service_ident: UUID or logical name of a service.
        """
        context = pecan.request.context
        cdict = context.to_policy_values()
        policy.authorize('iot:service:delete', cdict, cdict)

        rpc_service = api_utils.get_rpc_service(service_ident)
        pecan.request.rpcapi.destroy_service(pecan.request.context,
                                            rpc_service.uuid)

    @expose.expose(Service, types.uuid_or_name, body=Service, status_code=200)
    def patch(self, service_ident, val_Service):
        """Update a service.

        :param service_ident: UUID or logical name of a service.
        :param Service: values to be changed
        :return updated_service: updated_service
        """

        rpc_service = api_utils.get_rpc_service(service_ident)
        cdict = pecan.request.context.to_policy_values()
        cdict['project'] = rpc_service.project
        policy.authorize('iot:service:update', cdict, cdict)

        val_Service = val_Service.as_dict()
        for key in val_Service:
            try:
                rpc_service[key] = val_Service[key]
            except Exception:
                pass

        updated_service = pecan.request.rpcapi.update_service(
            pecan.request.context, rpc_service)
        return Service.convert_with_links(updated_service)

    @expose.expose(ServiceCollection, types.uuid, int, wtypes.text,
                   wtypes.text, types.listtype, types.boolean, types.boolean)
    def detail(self, marker=None,
               limit=None, sort_key='id', sort_dir='asc',
               fields=None, with_public=False, all_services=False):
        """Retrieve a list of services.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
                      This value cannot be larger than the value of max_limit
                      in the [api] section of the ironic configuration, or only
                      max_limit resources will be returned.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param with_public: Optional boolean to get also public service.
        :param all_services: Optional boolean to get all the services.
                            Only for the admin
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """

        cdict = pecan.request.context.to_policy_values()
        policy.authorize('iot:service:get', cdict, cdict)

        # /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "services":
            raise exception.HTTPNotFound()

        return self._get_services_collection(marker,
                                            limit, sort_key, sort_dir,
                                            with_public=with_public,
                                            all_services=all_services,
                                            fields=fields)
