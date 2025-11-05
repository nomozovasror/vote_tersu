from sqlalchemy import Column, Integer, String, Boolean, Date, Text
from ..core.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    image = Column(String, nullable=True)
    birth_date = Column(Date, nullable=True)
    degree = Column(String, nullable=True)
    which_position = Column(String, nullable=True)
    position = Column(String, nullable=True)
    election_time = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    from_api = Column(Boolean, default=False)
    external_id = Column(Integer, nullable=True)
