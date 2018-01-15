===============================
IoTronic
===============================

IoTronic is an Internet of Things resource management service for OpenStack clouds.

IoTronic allows to manage Internet of Things resources as part of an OpenStack data center.

* Free software: Apache license
* Source: https://git.openstack.org/cgit/openstack/iotronic/
* Bugs: https://bugs.launchpad.net/iotronic

.. contents:: Contents:
   :local:

Basic scenario
----------------------
For this installation of the Iotronic Service we are considering a scenario with the following hosts and softwares:

- Controller ( **Ubuntu linux**): Mysql, Keystone, Rabbitmq
- Iotronic ( **Ubuntu linux** ): Iotronic-conductor, iotronic-wamp-agent, crossbar
- Board: iotronic-lightining-rod

Controller host setup
----------------------
According to the `Openstack Documentation <https://docs.openstack.org/>`_ install the following softwares on the controller host:

- SQL database
- Message queue
- Memcached
- Keystone
   
Creation of the database
----------------------
On the dbms create the iotronic db and configure the access for the user iotronic::

    MariaDB [(none)]> CREATE DATABASE iotronic;
    MariaDB [(none)]> GRANT ALL PRIVILEGES ON iotronic.* TO iotronic@'localhost' IDENTIFIED BY ‘IOTRONIC_DBPASS’;
    MariaDB [(none)]> GRANT ALL PRIVILEGES ON iotronic.* TO iotronic@'%' IDENTIFIED BY ‘IOTRONIC_DBPASS’;

Add the user and the enpoints on Keystone::

    source adminrc
    openstack service create iot --name Iotronic
    openstack user create --password-prompt iotronic
    
    openstack role add --project service --user iotronic admin
    openstack role add admin_iot_project
    openstack role add manager_iot_project
    openstack role add user_iot

    openstack endpoint create --region RegionOne iot public http://IP_IOTRONIC:1288
    openstack endpoint create --region RegionOne iot internal http://IP_IOTRONIC:1288
    openstack endpoint create --region RegionOne iot admin http://1IP_IOTRONIC:1288


Configuring Iotronic Host 
----------------------

Crossbar
^^^^^^^^^^^^^^^^^^^^^
Install crossbar on the Iotronic host following the `official guide <https://crossbar.io/docs/Installation-on-Linux/>`_


Iotronic Installation 
^^^^^^^^^^^^^^^^^^^^^
Get the source::

    git clone https://github.com/openstack/iotronic.git

install the python-mysqldb::

    sudo apt-get install python-mysqldb 

and Iotronic::

    cd iotronic
    sudo pip install -r requirements.txt
    sudo pip install twisted
    sudo pip install paramiko
    sudo python setup.py install

create a log dir::

    mkdir -p /var/log/iotronic

populate the database::

    cd iotronic/utils
    ./loaddb MYSQL_IP_ON_CONTROLLER

API Service Configuration
^^^^^^^^^^^^^^^^^^^^^
Install apache and the other components::

sudo apt-get install apache2 python-setuptools libapache2-mod-wsgi libssl-dev

create ``/etc/apache2/conf-enabled/iotronic.conf`` and copy the following content::

    Listen 1288
    <VirtualHost *:1288>
        WSGIDaemonProcess iotronic 
        #user=root group=root threads=10 display-name=%{GROUP}
        WSGIScriptAlias / /var/www/cgi-bin/iotronic/app.wsgi

        #SetEnv APACHE_RUN_USER stack
        #SetEnv APACHE_RUN_GROUP stack
        WSGIProcessGroup iotronic

        ErrorLog /var/log/iotronic/iotronic-api_error.log
        LogLevel debug
        CustomLog /var/log/iotronic/iotronic-api_access.log combined

        <Directory /etc/iotronic>
            WSGIProcessGroup iotronic
            WSGIApplicationGroup %{GLOBAL}
            AllowOverride All
            Require all granted
        </Directory>
    </VirtualHost>

edit ``/etc/iotronic/iotronic.conf`` with the correct configuration.

There is just one wamp-agent and it must be set as the registration agent::
 
  register_agent = True

restart apache::
  
  systemctl restart apache2

Start the service (better use screen)::

  screen -S conductor
  iotronic-conductor

  screen -S agent
  iotronic-wamp-agent

Board Side 
----------------------

Follow the `iotronic-lightning-rod README <https://github.com/openstack/iotronic-lightning-rod/blob/master/README.rst>`_

