# Copyright 2017 MDSLAB - University of Messina
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

from iotronic.wamp.proxies.proxy import Proxy
from oslo_config import cfg
from oslo_log import log as logging
from subprocess import call

LOG = logging.getLogger(__name__)

nginx_opts = [
    cfg.StrOpt('nginx_path',
               default='/etc/nginx/conf.d/iotronic',
               help=('Default Nginx Path')),
]

CONF = cfg.CONF
CONF.register_opts(nginx_opts, 'nginx')


def save_map(board, dns):
    fp = CONF.nginx.nginx_path + "/maps/map_" + board
    with open(fp, "w") as text_file:
        text_file.write("~" + board + "." + dns + " " + board + ";")


def save_upstream(board, https_port):
    fp = CONF.nginx.nginx_path + "/upstreams/upstream_" + board
    string = '''upstream {0} {{
    server localhost:{1} max_fails=3 fail_timeout=10s;
    }}
    '''.format(board, https_port)

    with open(fp, "w") as text_file:
        text_file.write("%s" % string)


def save_server(board, http_port, dns):
    fp = CONF.nginx.nginx_path + "/servers/" + board
    string = '''server {{
    listen              80;
    server_name         .{0}.{2};

    location / {{
        proxy_pass http://localhost:{1};
    }}
    }}
    '''.format(board, http_port, dns)

    with open(fp, "w") as text_file:
        text_file.write("%s" % string)


def remove(board):
    call(["rm",
          CONF.nginx.nginx_path + "/servers/" + board,
          CONF.nginx.nginx_path + "/upstreams/upstream_" + board,
          CONF.nginx.nginx_path + "/maps/map_" + board
          ])


class ProxyManager(Proxy):

    def __init__(self, dns):
        self.dns = dns
        super(ProxyManager, self).__init__("nginx")

    def reload_proxy(self, ctx):
        call(["nginx", "-s", "reload"])

    def enable_webservice(self, ctx, board, https_port, http_port):
        LOG.debug(
            'Enabling WebService with ports  %s for http and %s for https '
            'on board %s', http_port, https_port, board)
        save_map(board, self.dns)
        save_upstream(board, https_port)
        save_server(board, http_port, self.dns)

    def disable_webservice(self, ctx, board):
        LOG.debug('Disabling WebService on board %s',
                  board)
        remove(board)
