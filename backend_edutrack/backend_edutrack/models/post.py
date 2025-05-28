from sqlalchemy import Column, Integer, Table, ForeignKey, Text, DateTime, String, UniqueConstraint 
from sqlalchemy.orm import relationship
from datetime import datetime
from .meta import Base
from .url import URL  # Jika URL ada di file terpisah

class PostInteraction(Base):
    __tablename__ = 'post_interactions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    # 'type' bisa 'like' atau 'dislike'
    interaction_type = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relasi ke User dan Post
    user = relationship("User", back_populates="post_interactions")
    post = relationship("Post", back_populates="post_interactions")

    # Pastikan setiap user hanya bisa memiliki satu interaksi (like/dislike) per post
    __table_args__ = (UniqueConstraint('user_id', 'post_id', name='_user_post_uc'),)

    def __repr__(self):
        return f"<PostInteraction(user_id={self.user_id}, post_id={self.post_id}, type='{self.interaction_type}')>"


# Tabel relasi many-to-many
post_recommendations = Table(
    "post_recommendations",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("posts.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True)
)

post_references = Table(
    "post_references",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("posts.id", ondelete="CASCADE")),
    Column("url_id", Integer, ForeignKey("urls.id", ondelete="CASCADE")),
)

class Post(Base):
    __tablename__ = 'posts'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ForeignKey ke User (penulis)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    author = relationship("User", back_populates="posts")

    # Likes, dislikes
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)

    # Relasi komentar
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")

    # Many-to-many relasi referensi (URL)
    references = relationship(
        "URL",
        secondary=post_references,
        back_populates="posts"
    )

    # Many-to-many relasi rekomendasi oleh dosen
    recommended_by = relationship(
        "User",
        secondary=post_recommendations,
        back_populates="recommended_posts"
    )
    
    post_interactions = relationship("PostInteraction", back_populates="post")
