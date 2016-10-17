from .model import engine, Base

def init_hydroshare_gis_layers_db(first_time):
    Base.metadata.create_all(engine)