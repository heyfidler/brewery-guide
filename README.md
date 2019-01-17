# Seattle Brewery Guide

Catalog of some of Seattle's breweries and beers.  Built using flask, sqlalchemy, and oauth2client to provide a secure catalog with CRUD capabilites. 


## Dependencies
built using
- Flask==1.0.2                
- Flask-HTTPAuth==3.2.4       
- Flask-SQLAlchemy==2.3.2     
- httplib2==0.12.0            
- Jinja2==2.10                
- oauth2client==4.1.3         
- SQLAlchemy==1.2.15          

## Usage

- initialize the VM `vagrant up`
- connect to VM `vagrant ssh`
- start the server `python project.py`
- connect your browser to `http://localhost:5000`
- JSON output available at `http://localhost:5000/brewery/JSON` for breweries and `http://localhost:5000/brewery/<brewery id>/beer/JSON` for beer list


