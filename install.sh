#! /bin/bash

function build_install {
    python setup.py build
    python setup.py install
    cp utils/iotronic_curl_client /usr/bin/iotronic
}

function restart_apache {
if which apache2 ; then
    systemctl restart apache2
else
    systemctl restart httpd
fi
}

case "$1" in
    api)
        build_install
        restart_apache
        ;;

    conductor)
        build_install
        cp bin/iotronic-conductor /usr/bin/
        ;;
        
    wamp-agent)
        build_install
        cp bin/iotronic-wamp-agent /usr/bin/
        ;;
        
    all)
        build_install
        restart_apache
        cp bin/iotronic-conductor /usr/bin/
        cp bin/iotronic-wamp-agent /usr/bin/
        ;;
        
    *)
        echo $"Usage: $0 {api|conductor|wamp-agent|all}"
        exit 1
esac
