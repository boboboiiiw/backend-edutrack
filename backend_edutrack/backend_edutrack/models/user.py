from sqlalchemy import Column, Integer, String, Text, Table
from sqlalchemy.orm import relationship
from .meta import Base
from .post import Post
from .comment import Comment

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password = Column(Text, nullable=False)

    role = Column(String(50), nullable=False, default='Mahasiswa')
    prodi = Column(String(255), nullable=True)
    nim = Column(String(20), unique=True, nullable=True) # Tambahkan kolom NIM di sini

    # Relasi ke Post
    posts = relationship("Post", back_populates="author")

    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")

    post_interactions = relationship("PostInteraction", back_populates="user")

    # Relasi ke rekomendasi (Many-to-many)
    recommended_posts = relationship(
        "Post",
        secondary="post_recommendations",
        back_populates="recommended_by"
    )