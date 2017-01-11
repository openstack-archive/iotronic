#! /bin/bash

function build_install {
    python setup.py build
    python setup.py install
    rm -rf build
    rm -rf iotronic.egg-info
    rm -rf dist
}
case "$1" in
    iotronic)
        build_install
        systemctl restart httpd
        cp bin/iotronic-conductor /usr/bin/
        ;;
        
    wamp-agent)
        build_install
        cp bin/iotronic-wamp-agent /usr/bin/
        ;;
        
    all)
        build_install
        systemctl restart httpd
        cp bin/iotronic-conductor /usr/bin/
        cp bin/iotronic-wamp-agent /usr/bin/
        ;;
        
    *)
        echo $"Usage: $0 {iotronic|wamp-agent|all}"
        exit 1
esac