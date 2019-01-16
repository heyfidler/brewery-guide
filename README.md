#Seattle Brewery Guide

Catalog of some of Seattle's breweries and beers.  Built using flask, sqlalchemy, and oauth2client to provide a secure catalog with CRUD capabilites. 

## Usage

- initialize the VM `vagrant up`
- connect to VM `vagrant ssh`
- start the server `python project.py`
- connect your browser to `http://localhost:5000`
- JSON output available at `http://localhost:5000/brewery/JSON` for breweries and `http://localhost:5000/brewery/<brewery id>/beer/JSON` for beer list


