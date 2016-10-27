from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Date, String, Text
from sqlalchemy.orm import sessionmaker

from .app import HydroshareGis

engine = HydroshareGis.get_persistent_store_engine('hydroshare_gis_layers')
SessionMaker = sessionmaker(bind=engine)
Base = declarative_base()


class Layer(Base):
    """
    Example SQLAlchemy DB Model
    """
    # From the database, a library of event details are packaged together
    __tablename__ = 'gis_layers'

    # Columns
    id = Column(Integer, primary_key=True)
    layer_id = Column(String(100))
    associated_res_id = Column(String(50))
    res_mod_date = Column(String(50), nullable=True)
    name = Column(String(300), nullable=True)
    associated_file_name = Column(String(300), nullable=True)
    associated_res_type = Column(String(50), nullable=True)
    extents = Column(Text, nullable=True)
    attributes = Column(String(1000), nullable=True)
    geom_type = Column(String(50), nullable=True)
    band_info = Column(String(300), nullable=True)
    site_info = Column(String(1000), nullable=True)

    def __init__(self, layer_id, res_id, res_mod_date, layer_name, file_name, res_type, extents, attributes, geom_type,
                 band_info, site_info):
        """
        Constructor for an event
        """
        self.layer_id = layer_id
        self.associated_res_id = res_id
        self.res_mod_date = res_mod_date
        self.name = layer_name
        self.associated_file_name = file_name
        self.associated_res_type = res_type
        self.extents = extents
        self.attributes = attributes
        self.geom_type = geom_type
        self.band_info = band_info
        self.site_info = site_info


    @staticmethod
    def get_layers_by_associated_res_id(res_id):
        session = SessionMaker()
        res_layers = session.query(Layer).filter(Layer.associated_res_id == res_id).all()
        session.close()

        return res_layers

    @staticmethod
    def add_layer_to_database(res_id, res_type, layer_name, layer_id, layer_extents, layer_attributes, geom_type,
                              band_info, site_info, public_fname, res_mod_date):

        session = SessionMaker()
        session.add(Layer(layer_id, res_id, res_mod_date, layer_name, public_fname, res_type, layer_extents, layer_attributes, geom_type,
                          band_info, site_info))
        session.commit()

    @staticmethod
    def remove_layer_by_res_id(res_id):
        session = SessionMaker()
        session.query(Layer).filter(Layer.associated_res_id == res_id).delete()
        session.commit()


class ResourceLayersCount:
    def __init__(self):
        self.file_count = 0

    def increase(self):
        self.file_count += 1

    def decrease(self):
        self.file_count -= 1

    def reset(self):
        self.file_count = 0

    def get(self):
        return self.file_count
