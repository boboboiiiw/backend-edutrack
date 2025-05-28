from sqlalchemy import Column, Integer, String
from .meta import Base
from sqlalchemy.orm import relationship

class URL(Base):
    __tablename__ = 'urls'

    id = Column(Integer, primary_key=True)
    url = Column(String(500), unique=True, nullable=False)

    # Many-to-many relationship back to Post
    posts = relationship(
        "Post",
        secondary="post_references",  # Tabel relasi many-to-many
        back_populates="references"
    )
