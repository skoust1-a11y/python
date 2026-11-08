"""Core RAG service orchestrating multi-modal document processing and querying."""
import logging
import os
import tempfile
from typing import List, Optional, Dict, Any, Tuple

from dotenv import load_dotenv
from llama_parse import LlamaParse
from llama_index.core import VectorStoreIndex, Document, Settings,StorageContext
from llama_index.core.schema import TextNode
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.vector_stores.postgres import PGVectorStore

from .metadata import get_file_metadata, extract_diet_metadata_from_filename
from .semantic_chunking import SemanticChunker
from .table_extraction import find_markdown_tables
from .table_processing import build_nodes_from_tables
from .image_extraction import extract_images_from_pdf
from .captioning import generate_caption
from .query_engine import create_query_engine
from llama_index.core.schema import BaseNode

logger = logging.getLogger(__name__)

class NodeInsertionError(Exception):
    """Raised when inserting nodes into the index fails."""
    pass

def configure_llm_and_embeddings() -> Tuple[AzureOpenAI, AzureOpenAIEmbedding]:
    """
    Configure LLM and embedding models from environment variables.

    Returns:
        Tuple of (llm, embed_model)

    Raises:
        EnvironmentError: If required environment variables are missing
    """
    load_dotenv()
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    llm_deployment = os.environ.get("AZURE_OPENAI_LLM_DEPLOYMENT")
    embedding_deployment = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

    missing = [
        name
        for name, val in [
            ("AZURE_OPENAI_API_KEY", api_key),
            ("AZURE_OPENAI_ENDPOINT", endpoint),
            ("AZURE_OPENAI_LLM_DEPLOYMENT", llm_deployment),
            ("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", embedding_deployment),
        ]
        if not val
    ]
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        raise EnvironmentError("Missing environment variables: " + ", ".join(missing))

    logger.info(f"Configuring Azure OpenAI LLM: deployment={llm_deployment}, endpoint={endpoint}")
    llm_model_name = os.getenv('AZURE_OPENAI_LLM_MODEL', 'gpt-4o-mini')
    llm = AzureOpenAI(
            model=llm_model_name,
            deployment_name=llm_deployment,
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
            temperature=0.1,
            max_completion_tokens=1000,
        )

    logger.info(f"Configuring Azure OpenAI Embedding: deployment={embedding_deployment}")
    embed_model = AzureOpenAIEmbedding(
        model=embedding_deployment,
        deployment_name=embedding_deployment,
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
    )

    try:
        Settings.llm = llm
        Settings.embed_model = embed_model
    except Exception as e:
        logger.warning(f"Could not set global Settings: {e}, models will be passed directly")

    logger.info("LLM and embedding models configured successfully")
    return llm, embed_model


def load_documents(pdf_path: str) -> str:
    """
    Load and parse PDF document to markdown using LlamaParse.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Full markdown text from the document
    """
    logger.info(f"Loading PDF document: {pdf_path}")
    llama_parse_api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not llama_parse_api_key:
        logger.error("Missing LLAMA_CLOUD_API_KEY in environment")
        raise SystemExit(
            "Missing LLAMA_CLOUD_API_KEY in environment. Get one from https://cloud.llamaindex.ai/"
        )

    logger.info("Initializing LlamaParse parser...")
    parser_lp = LlamaParse(api_key=llama_parse_api_key,result_type="markdown", verbose=True)
    documents : List[Document] = parser_lp.load_data(pdf_path)

    if not documents:
        logger.error("No content returned by LlamaParse")
        raise SystemExit("No content returned by LlamaParse.")

    full_text = "\n\n".join(doc.text for doc in documents if getattr(doc, "text", ""))
    if not full_text.strip():
        logger.error("Parsed document appears empty")
        raise SystemExit("Parsed document appears empty.")

    logger.info(f"Document parsed successfully, extracted {len(full_text)} characters of text")
    return full_text


def create_vector_store(embed_dim: int = 1536) -> PGVectorStore:
    """
    Create a PostgreSQL vector store instance.

    Args:
        embed_dim: Dimension of the embeddings

    Returns:
        PGVectorStore instance
    """
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME", "rag_db")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD")
    table_name = os.getenv("DB_TABLE_NAME")

    if not password:
        logger.error("DB_PASSWORD environment variable is required")
        raise EnvironmentError("DB_PASSWORD environment variable is required")

    if not table_name:
        logger.error("DB_TABLE_NAME environment variable is required")
        raise EnvironmentError(
            "DB_TABLE_NAME environment variable is required. Please set it in your .env file."
        )

    logger.info(f"Using table name from DB_TABLE_NAME environment variable: {table_name}")
    return PGVectorStore.from_params(
        database=database,
        host=host,
        password=password,
        port=int(port),
        user=user,
        table_name=table_name,
        embed_dim=embed_dim,
    )


class RAGService:
    """Core service for multi-modal diet counselling RAG system."""
    
    def __init__(self):
        """Initialize the RAG service."""
        self.index: Optional[VectorStoreIndex] = None
        self.llm = None
        self.embed_model = None
        self.semantic_chunker = None
        self._initialized = False
        self._index_loaded = False
    
    def initialize(self):
        """Initialize LLM, embeddings, and processors."""
        if not self._initialized:
            logger.info("Initializing LLM and embedding models...")
            self.llm, self.embed_model = configure_llm_and_embeddings()
            
            # Initialize semantic chunker
            self.semantic_chunker = SemanticChunker(self.embed_model)
            
            self._initialized = True
            logger.info("RAG service initialized successfully")
            
            # Try to load existing index after initialization
            if not self._index_loaded:
                self._load_existing_index()
    
    def _load_existing_index(self):
        """Load existing index from PostgreSQL if it exists."""
        if self._index_loaded:
            return
        
        self._index_loaded = True
        
        try:
            logger.info("Attempting to load existing index from PostgreSQL...")
            
            if not self._initialized:
                self.initialize()
            
            vector_store = create_vector_store(embed_dim=1536)
            
            try:
                Settings.embed_model = self.embed_model
                index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
            except Exception as e1:
                logger.debug(f"First attempt to load index failed: {e1}, trying with explicit embed_model...")
                try:
                    index = VectorStoreIndex.from_vector_store(
                        vector_store=vector_store,
                        embed_model=self.embed_model
                    )
                except Exception as e2:
                    logger.debug(f"Second attempt to load index failed: {e2}")
                    raise e2
            
            self.index = index
            logger.info("Successfully loaded existing index from PostgreSQL")
        except Exception as e:
            logger.info(f"No existing index found in PostgreSQL (this is normal for first run): {type(e).__name__}: {e}")
            self.index = None
    
    def process_document(
        self,
        pdf_path: str,
        original_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a PDF document and add it to the multi-modal index.
        
        Processes text (with semantic chunking), tables, and images.
        
        Args:
            pdf_path: Path to the PDF file (may be temporary)
            original_filename: Original filename to use in metadata
            
        Returns:
            Dictionary with processing results including node statistics
        """
        logger.info("Processing document (boilerplate): %s", pdf_path)

        # TODO: Process the document and index it into the vector store, then return a result dict.
        # HINT: Ensure services are initialized (LLM, embedding model, semantic chunker, etc.)
        # HINT: Build metadata using `get_file_metadata(pdf_path)`
        # HINT: If `original_filename` is provided, override `source`/`file_path` and re-extract
        #       diet tags using `extract_diet_metadata_from_filename(original_filename)`
        # HINT: Parse the PDF into plain text/markdown (extract tables/images if present)
        # HINT: Turn the parsed content into nodes/chunks and attach metadata to each node
        # HINT: Create/load the vector store using `create_vector_store(...)`
        # HINT: Create or load a `VectorStoreIndex`, then insert nodes into it
        # HINT: Return a dict like:
        #   - message: str
        #   - documents_indexed: int
        #   - optional: total_nodes/text_nodes/table_nodes/image_nodes, file_path, etc.
        # Your code here:
        try:
            if not self._initialized:
                self.initialize()
            metadata = get_file_metadata(file_path=pdf_path)
            if original_filename:
                source_name = original_filename
                metadata["source"] = original_filename
                metadata = extract_diet_metadata_from_filename(metadata.get('source'))
            else:
                source_name = metadata.get("source", pdf_path)
            full_text = load_documents(pdf_path)


            all_nodes: List[BaseNode] = []
            length_of_text_nodes = 0
            length_of_table_nodes = 0
            length_of_image_nodes = 0

            # Step 3: Extract and process tables from document (process first)
            logger.info("Step 3: Extracting markdown tables from document...")
            table_tuples = find_markdown_tables(full_text)
            if table_tuples:
                table_markdowns = [t[2] for t in table_tuples]
                table_nodes = build_nodes_from_tables(
                    source_name=source_name,
                    table_markdowns=table_markdowns,
                    llm=self.llm,
                    additional_metadata=metadata,
                )
                length_of_table_nodes = len(table_nodes)
                for node in table_nodes:
                   if hasattr(node,'metadata'):
                       if hasattr(node.metadata,'content_type') and node.metadata['content_type'] == 'table_summary':
                           logger.info(f'The metadata of the table node index: {node.metadata['table_index']} is:{node.metadata}')  
                logger.info(f'The metadata of the table nodes are inserted')
                all_nodes.extend(table_nodes)

            # Extract and process images (process second)
            os.makedirs("Documents", exist_ok=True)
            output_dir = "Documents"
            images = extract_images_from_pdf(pdf_path=pdf_path, output_dir=output_dir)
            if images:
                for image in images:
                    meta = {
                        'content_type': "image_caption",
                        'page_index': image['page'],
                        'image_index': image['image_index'],
                        'image_path':image['path']
                    }
                    imageNode = TextNode(
                        text=generate_caption(image['path']),
                        metadata={**metadata, **meta}
                    )
                    length_of_image_nodes += 1
                    all_nodes.append(imageNode)

            # Always process text content with semantic chunking so text, tables and images are all indexed
            logger.info("Processing text content with semantic chunking (always run)...")
            text_nodes = self.semantic_chunker.process(
                full_text,
                metadata={"source": source_name, "page": "all", **metadata},
            )
            length_of_text_nodes = len(text_nodes)
            all_nodes.extend(text_nodes)
            logger.info(f"Created {len(text_nodes)} text nodes")

            # Prepare vector store and deterministically load or create the index before inserting nodes
            vector_store = create_vector_store(embed_dim=1536)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            try:
                # Try to load existing index from this vector store
                Settings.embed_model = self.embed_model
                index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
                logger.info("Loaded existing index from vector store")
            except Exception as e_load:
                logger.info(f"No existing index found in vector store or failed to load ({type(e_load).__name__}): {e_load}; creating a new index.")
                index = VectorStoreIndex(nodes=[], embed_model=self.embed_model, storage_context=storage_context)

            # Assign index to self.index deterministically
            self.index = index

            try:
                for node in all_nodes:
                    self.index.insert(node)
            except NodeInsertionError as e:
                raise NodeInsertionError(f'The Nodes are not inserted correctly..:{e}')
            except Exception:
                raise
#   - message: str
#   - documents_indexed: int
#   - optional: total_nodes/text_nodes/table_nodes/image_nodes, file_path, etc.

            return {
                'message':f'Documents indexing done for {len(all_nodes)}',
                'documents_indexed':len(all_nodes),
                'total_nodes':len(all_nodes),
                'text_nodes':length_of_text_nodes,
                'table_nodes':length_of_table_nodes,
                'image_nodes':length_of_image_nodes
            }
        except Exception as e:
            raise
    
    def query(
        self,
        question: str,
        similarity_top_k: int = 2,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Any]]:
        """
        Query the index with optional metadata filtering.
        
        Args:
            question: Query question
            similarity_top_k: Number of top similar results to retrieve
            filters: Optional metadata filters (e.g., {"meal_type": "breakfast", "dietary_restriction": "vegetarian"})
            
        Returns:
            Tuple of (answer string, list of retrieved nodes)
        """
        # Try to load existing index if not already loaded
        if not self.index and not self._index_loaded:
            self._load_existing_index()
        
        if not self.index:
            raise ValueError("Index not initialized. Please process a document first.")
        
        logger.info(f"Processing query: question='{question[:100]}...', similarity_top_k={similarity_top_k}, filters={filters}")

        query_engine = create_query_engine(
            index=self.index,
            llm=self.llm,
            similarity_top_k=similarity_top_k,
            filters=filters,
        )

        response = query_engine.query(question)
        answer = str(response.response) if hasattr(response, "response") else str(response)
        nodes = []
        if hasattr(response, "source_nodes") and response.source_nodes:
            nodes = response.source_nodes
        
        logger.info(f"Query completed, answer generated (length: {len(answer)} characters), {len(nodes)} nodes retrieved")
        
        return answer, nodes
    
    def is_initialized(self) -> bool:
        """Check if the service has been initialized with a document."""
        if not self.index and not self._index_loaded:
            try:
                self._load_existing_index()
            except Exception:
                pass
        return self.index is not None
