"""
pgvector models for RAG retrieval
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime
from app.core.database import Base


class Collection(Base):
    """Document collection with embedding configuration."""
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_public = Column(Boolean, default=False)
    embedding_provider = Column(String)  # openai, cohere, google, anthropic
    embedding_model = Column(String)     # text-embedding-ada-002, etc.

    # Relationships
    documents = relationship("Document", back_populates="collection")

    def __repr__(self):
        return f"<Collection(id={self.id}, name='{self.name}', model='{self.embedding_model}')>"


class Document(Base):
    """Uploaded document with metadata."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String)  # pdf, txt, docx, md, etc.
    content = Column(Text)      # Full document text
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    metadata_ = Column("metadata", Text)     # JSON metadata as string (column name 'metadata', attribute name 'metadata_')
    collection_id = Column(Integer, ForeignKey("collections.id"), index=True)

    # Relationships
    collection = relationship("Collection", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', collection_id={self.collection_id})>"


class DocumentChunk(Base):
    """Text chunk with vector embedding for RAG retrieval."""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer)  # Position in document
    embedding = Column(Vector(1536), nullable=False)  # Vector embedding
    provider = Column(String)      # Embedding provider used
    model = Column(String)         # Embedding model used
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"
