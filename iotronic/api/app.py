# -*- encoding: utf-8 -*-

# Copyright © 2012 New Dream Network, LLC (DreamHost)
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


from iotronic.api import config
from iotronic.api.controllers import base
from iotronic.api import hooks
from iotronic.api import middleware

from iotronic.api.middleware import auth_token
from oslo_config import cfg
import oslo_middleware.cors as cors_middleware
import pecan
from pecan import make_app

opts = [
    cfg.StrOpt(
        'auth_strategy',
        default='keystone',
        help=('Authentication strategy used by iotronic-api: "keystone" '
              'or "noauth". "noauth" should not be used in a production '
              'environment because all authentication will be disabled.')),
    cfg.BoolOpt('debug_tracebacks_in_api',
                default=False,
                help=('Return server tracebacks in the API response for any '
                      'error responses. WARNING: this is insecure '
                      'and should not be used in a production environment.')),
    cfg.BoolOpt(
        'pecan_debug',
        default=False,
        help=(
            'Enable pecan debug mode. WARNING: this is insecure '
            'and should not be used in a production environment.')),
]

api_opts = [
    cfg.StrOpt('host_ip',
               default='0.0.0.0',
               help=('The IP address on which iotronic-api listens.')),
    cfg.PortOpt('port',
                default=1288,
                help=('The TCP port on which iotronic-api listens.')),
    cfg.IntOpt('max_limit',
               default=1000,
               help=('The maximum number of items returned in a single '
                     'response from a collection resource.')),
    cfg.StrOpt('public_endpoint',
               help=("Public URL to use when building the links to the API "
                     "resources."
                     " If None the links will be built using the request's "
                     "host URL. If the API is operating behind a proxy, you "
                     "will want to change this to represent the proxy's URL. "
                     "Defaults to None.")),
    cfg.IntOpt('api_workers',
               help=('Number of workers for OpenStack Iotronic API service. '
                     'The default is equal to the number of CPUs available '
                     'if that can be determined, else a default worker '
                     'count of 1 is returned.')),
    cfg.BoolOpt('enable_ssl_api',
                default=False,
                help=("Enable the integrated stand-alone API to service "
                      "requests via HTTPS instead of HTTP. If there is a "
                      "front-end service performing HTTPS offloading from "
                      "the service, this option should be False; note, you "
                      "will want to change public API endpoint to represent "
                      "SSL termination URL with 'public_endpoint' option.")),
]

opt_group = cfg.OptGroup(name='api',
                         title='Options for the iotronic-api service')


CONF = cfg.CONF
CONF.register_opts(opts,)
CONF.register_opts(api_opts, 'api')


def get_pecan_config():
    # Set up the pecan configuration
    filename = config.__file__.replace('.pyc', '.py')
    return pecan.configuration.conf_from_file(filename)


def setup_app(config=None):

    app_hooks = [hooks.ConfigHook(),
                 hooks.DBHook(),
                 hooks.ContextHook(config.app.acl_public_routes),
                 hooks.RPCHook(),
                 hooks.NoExceptionTracebackHook(),
                 hooks.PublicUrlHook()]

    app_conf = dict(config.app)

    app = make_app(
        app_conf.pop('root'),
        hooks=app_hooks,
        force_canonical=getattr(config.app, 'force_canonical', True),
        wrap_app=middleware.ParsableErrorMiddleware,
        **app_conf
    )

    if CONF.auth_strategy == "keystone":
        app = auth_token.AuthTokenMiddleware(
            app, dict(cfg.CONF),
            public_api_routes=config.app.acl_public_routes)

    # Create a CORS wrapper, and attach iotronic-specific defaults that must be
    # included in all CORS responses.
    app = IotronicCORS(app, CONF)
    cors_middleware.set_defaults(
        allow_methods=['GET', 'PUT', 'POST', 'DELETE', 'PATCH'],
        expose_headers=[base.Version.max_string, base.Version.min_string,
                        base.Version.string]
    )

    return app


class IotronicCORS(cors_middleware.CORS):
    """Iotronic-specific CORS class
    We're adding the Iotronic-specific version headers to the list of simple
    headers in order that a request bearing those headers might be accepted by
    the Iotronic REST API.
    """
    simple_headers = cors_middleware.CORS.simple_headers + [
        'X-Auth-Token',
        base.Version.max_string,
        base.Version.min_string,
        base.Version.string
    ]


class VersionSelectorApplication(object):

    def __init__(self):
        pc = get_pecan_config()
        pc.app.enable_acl = (CONF.auth_strategy == 'keystone')
        self.v1 = setup_app(config=pc)

    def __call__(self, environ, start_response):
        return self.v1(environ, start_response)
