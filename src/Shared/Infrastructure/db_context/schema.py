from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base

metadata = MetaData()

base = declarative_base(metadata=metadata)
