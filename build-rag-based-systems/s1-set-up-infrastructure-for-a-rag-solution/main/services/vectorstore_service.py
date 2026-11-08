"""
Service module for managing vectorstore operations.
"""

import logging
from typing import List, Optional
from langchain_openai import AzureOpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document
from uuid import uuid4


# TODO: Import necessary modules here (Document, PGVector, AzureOpenAIEmbeddings, etc.)

from main.config import load_config

logger = logging.getLogger(__name__)


class VectorstoreService:
    """Service class for vectorstore operations."""
    
    def __init__(self):
        """Initialize the vectorstore service with embeddings and vectorstore."""
        self.config = load_config()
        self.embeddings = self._initialize_embeddings()
        self.vectorstore = self._initialize_vectorstore()
    
    def _initialize_embeddings(self):
        """Initialize Azure OpenAI embeddings."""
        try:
            # TODO: Initialize Azure OpenAI embeddings using config values
            # Access config values from self.config (azure_endpoint, azure_embedding_deployment, azure_api_key, api_version)
            embed_config = self.config
            embedding_model = AzureOpenAIEmbeddings(
                api_key=embed_config.get('azure_api_key'),
                azure_deployment=embed_config.get('azure_embedding_deployment'),
                azure_endpoint=embed_config.get('azure_endpoint'),
                api_version=embed_config.get('api_version'),
            )
            # Log success message
            logger.info('Azure OpenAI Embedding model intialized.')
            # Return the embeddings object
            return embedding_model
        except Exception as e:
            # TODO: Add exception handling here
            # Log error appropriately
            logger.error('AzureOpenAI embedding model not able to initialize.')
            # Re-raise the exception
            raise ValueError('Embedding model not intialized')
            pass
    
    def _initialize_vectorstore(self):
        """Initialize PGVector store."""
        try:
            # TODO: Initialize PGVector store
            # Use self.embeddings, collection_name from self.config, and database_url from self.config
            embed_config = self.config
            embedding_model = self.embeddings
            db = embed_config.get('database_url')
            collection_name = embed_config.get('collection_name') 

            pg_vector = PGVector(
                collection_name=collection_name,
                connection=db,
                embeddings=embedding_model,
            )
            # Log success message
            logger.info('Vector Store is Successfully initialized.')
            # Return the vectorstore object
            return pg_vector
        except Exception as e:
            # TODO: Add exception handling here
            # Log error appropriately
            logger.error('Vector Store instance not created.')
            # Re-raise the exception
            raise Exception('Vector Store instance not created.')
    
    def add_document(self, content: str, metadata: Optional[dict] = None) -> str:
        """
        Add a single document to the vectorstore.
        
        Args:
            content: The text content to add
            metadata: Optional metadata dictionary
            
        Returns:
            Document ID of the inserted document
        """
        try:
            # TODO: Create a Document object with content and metadata
            metadata_check = dict(metadata or {})

            if not metadata_check.get('id'):
                metadata_check['id'] = str(uuid4())
            if not metadata_check.get('document'):
                metadata_check['document'] = 'Smart_Advisor_Standard_Name'
             
            document = Document(page_content=content,metadata=metadata_check)

            # TODO: Add the document to the vectorstore using self.vectorstore
            vector_db = self.vectorstore

            vector_db.add_documents([document])
            # TODO: Get the document ID from the result

            current_doc_id = document.metadata.get('id')
            
            # TODO: Log success message with document ID
            logger.info(f"✓ Stored document with ID: {current_doc_id}")
            
            # TODO: Return the document ID
            return current_doc_id
        except Exception as e:
            # TODO: Add exception handling here
            # Log error appropriately
            logger.error('The Document has failed to add to the vector store.')
            # Re-raise the exception
            raise Exception('The Document has failed to add to the vector store.')
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        Add multiple documents to the vectorstore.
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of document IDs
        """
        try:
            # Ensure documents is a list of Document objects
            vector_db = self.vectorstore

            for doc in documents:
                # Normalize metadata and ensure required fields
                metadata_check = dict(doc.metadata or {})

                if not metadata_check.get('id'):
                    doc.metadata['id'] = str(uuid4())
                if not metadata_check.get('document'):
                    doc.metadata['document'] = 'Smart_Advisor_Standard_Name'

            # Add documents to the vector store
            vector_db.add_documents(documents)

            # Build list of ids from the documents
            list_of_ids = [doc.metadata.get('id') for doc in documents]

            # Log success message with number of documents added
            logger.info(f'Inserted {len(list_of_ids)} documents: {list_of_ids}')
            return list_of_ids
        except Exception as e:
            logger.error('The Documents has been failed to add to the vector store.')
            raise Exception('The Documents has been failed to add to the vector store.')
    
    def query(self, query_text: str, top_k: int = 1) -> List[dict]:
        """
        Query the vectorstore for similar documents.
        
        Args:
            query_text: The search query
            top_k: Number of results to return
            
        Returns:
            List of result dictionaries with content and metadata
        """
        try:
            # TODO: Perform similarity search using self.vectorstore
            vector_store = self.vectorstore

            results = vector_store.similarity_search_with_score(query=query_text,k=top_k)
            
            query_lists = []
            # TODO: Transform results into list of dictionaries with "content" and "metadata" keys
            for doc,score in results:
                doc_id = doc.metadata.get('id','standard_doc_id') if doc.metadata else None

                query_lists.append(
                    {
                        'content' : doc.page_content,
                        'metadata' : doc.metadata
                    }
                )
     
            # TODO: Return the list of result dictionaries
            return query_lists
        except Exception as e:
            # TODO: Add exception handling here
            # Log error appropriately
            logger.error('Semantic search not done properly..')
            # Re-raise the exception
            raise Exception('Semantic search Failed..')


# Global service instance (singleton pattern)
_vectorstore_service: Optional[VectorstoreService] = None


def get_vectorstore_service() -> VectorstoreService:
    """Get or create the global vectorstore service instance."""
    global _vectorstore_service
    # TODO: Implement singleton pattern
    # Check if _vectorstore_service is None, if so create a new instance
    if _vectorstore_service is None:
        _vectorstore_service = VectorstoreService()
    # Return the service instance
    return _vectorstore_service

