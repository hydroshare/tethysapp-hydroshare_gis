#HydroShare GIS
*tethysapp-hydroshare_gis*

**This app is created to run in the Teyths Platform programming environment.
See: https://github.com/tethysplatform/tethys and http://docs.tethysplatform.org/en/latest/**

##Prerequisites:
- Tethys Platform (CKAN, PostgresQL, GeoServer)
- hs_restclient-python (Python package)
- pyshp (Python package)

###Install Tathys Platform
See: http://docs.tethysplatform.org/en/latest/installation.html

###Install hs_restclient:
See: http://hs-restclient.readthedocs.org/en/latest/#installation

###Install pyshp into Tethys' Python environment:
```
$ sudo su
$ . /usr/lib/tethys/bin/activate
$ pip install pyshp
$ exit
```
##Installation:
Clone the app into the directory you want:
```
$ git clone https://github.com/shawncrawley/tethysapp-hydroshare_gis.git
$ cd tethysapp-hydroshare_gis
```

Then install the app into the Tethys Platform.

###Installation for App Development:
```
$ . /usr/lib/tethys/bin/activate
$ cd tethysapp-hydroshare_gis
$ python setup.py develop
```
###Installation for Production:
```
$ . /usr/lib/tethys/bin/activate
$ cd tethysapp-hydroshare_gis
$ python setup.py install
$ tethys manage collectstatic
```
Restart the Apache Server:
See: http://docs.tethysplatform.org/en/latest/production/installation.html#enable-site-and-restart-apache

##Updating the App:
Update the local repository and Tethys Platform instance.
```
$ . /usr/lib/tethys/bin/activate
$ cd tethysapp-hydroshare_gis
$ git pull
```
Restart the Apache Server:
See: http://docs.tethysplatform.org/en/latest/production/installation.html#enable-site-and-restart-apache

##Fin
