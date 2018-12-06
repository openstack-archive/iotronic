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

from designateclient.v2 import client

from keystoneauth1.identity import generic
from keystoneauth1 import session as keystone_session
from oslo_config import cfg

CONF = cfg.CONF

designate_opts = [
    cfg.StrOpt('url',
               default='http://localhost:9696/',
               help=('URL designate')),
    cfg.StrOpt('retries',
               default=3,
               help=('retries designate')),
    cfg.StrOpt('auth_strategy',
               default='noauth',
               help=('auth_strategy designate')),
    cfg.StrOpt('username',
               default='designate',
               help=('designate username')),
    cfg.StrOpt('password',
               default='',
               help=('password')),
    cfg.StrOpt('project_name',
               default='service',
               help=('service')),
    cfg.StrOpt('project_domain_name',
               default='default',
               help=('domain id')),
    cfg.StrOpt('auth_url',
               default='http://localhost:35357',
               help=('auth')),
    cfg.StrOpt('project_domain_id',
               default='default',
               help=('project domain id')),
    cfg.StrOpt('user_domain_id',
               default='default',
               help=('user domain id')),
]

CONF.register_opts(designate_opts, 'designate')


def get_client():
    auth = generic.Password(
        auth_url=CONF.designate.auth_url,
        username=CONF.designate.username,
        password=CONF.designate.password,
        project_name=CONF.designate.project_name,
        project_domain_id=CONF.designate.project_domain_id,
        user_domain_id=CONF.designate.user_domain_id,
    )

    session = keystone_session.Session(auth=auth)
    cl = client.Client(session=session)
    return cl


def create_record(name, ip, zone_name):
    client = get_client()
    zone = client.zones.get(zone_name + ".")
    record = None
    try:
        record = client.recordsets.get(zone["id"], name + "." + zone["name"])
    except Exception:
        pass
    if not record:
        client.recordsets.create(zone["id"], name, 'A', [ip])


def delete_record(name, zone_name):
    client = get_client()
    zone = client.zones.get(zone_name + ".")
    try:
        record = client.recordsets.get(zone["id"], name + "." + zone["name"])
    except Exception:
        pass
    if record:
        client.recordsets.delete(zone["id"], name + "." + zone["name"])
