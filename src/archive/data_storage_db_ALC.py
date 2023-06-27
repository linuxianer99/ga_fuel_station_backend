from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import Column, DateTime
from sqlalchemy import create_engine
from sqlalchemy import Float
import sqlalchemy as db

import time
import logging
logging.basicConfig(level=logging.DEBUG)



class Base(DeclarativeBase):
    pass

class Refueling(Base):
    __tablename__ = 'fuel'

    id: Mapped[int] = mapped_column(primary_key=True)
    aircraft: Mapped[str] = mapped_column(String(30))
    article: Mapped[str] = mapped_column(String(30))
    amount: Mapped[float] = mapped_column(Float)
    totalizer: Mapped[float] = mapped_column(Float)
    created_date = Column(DateTime(timezone=True), default=func.now())


class storage(object):
    def __init__(self, config):
        # connect to database
        logging.info("Connecting to database ...")
        retry_count = 0
        retry = True
        connection_string = config['database']['connection_string']
        while retry and retry_count < 20:
            try:
                print("aha")
                engine = db.create_engine(connection_string, echo=True)
                conn = engine.connect()
                metadata = db.MetaData()
                refueling = db.Table(config['database']['db_table'], metadata, autoload=True, autoload_with=engine)
                retry = False
                logging.info("Database connection OK")
            except:
                retry_count = retry_count + 1
                retry = True
                time.sleep(5)
                logging.error("Database connection failed ... retrying ... %i ", retry_count)



