#!/usr/bin/env python3
"""
PostgreSQL backend for embeddings with proper setup and permission checks
"""

import json
import logging
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

logger = logging.getLogger(__name__)

class PostgreSQLEmbeddingsBackend:
    """PostgreSQL with pgvector backend with full setup and permission checks"""
    
    def __init__(self, connection_url: str, embedding_dim: int = 768, 
                 embedding_function=None, auto_setup: bool = True):
        """
        Initialize PostgreSQL backend
        
        Args:
            connection_url: PostgreSQL connection URL
            embedding_dim: Dimension of embeddings
            embedding_function: Function to generate embeddings
            auto_setup: Automatically create database and tables if missing
        """
        self.connection_url = connection_url
        self.embedding_dim = embedding_dim
        self.embedding_function = embedding_function
        self.auto_setup = auto_setup
        self.conn = None
        
        # Parse connection URL
        self.parsed_url = urlparse(connection_url)
        self.db_name = self.parsed_url.path[1:] if self.parsed_url.path else 'embeddings'
        
        # Setup connection
        self._setup_connection()
    
    def _check_permissions(self, conn) -> Dict[str, bool]:
        """Check database permissions"""
        permissions = {
            'create_database': False,
            'create_extension': False,
            'create_table': False,
            'insert': False,
            'select': False,
            'create_index': False
        }
        
        with conn.cursor() as cur:
            # Check if user can create databases
            try:
                cur.execute("""
                    SELECT has_database_privilege(current_user, NULL, 'CREATE')
                """)
                permissions['create_database'] = cur.fetchone()[0]
            except (psycopg2.Error, Exception) as e:
                logger.debug(f"Could not check create database privilege: {e}")
                pass
            
            # Check if user is superuser (needed for CREATE EXTENSION)
            try:
                cur.execute("SELECT current_setting('is_superuser')")
                permissions['create_extension'] = cur.fetchone()[0] == 'on'
            except (psycopg2.Error, Exception) as e:
                logger.debug(f"Could not check superuser status: {e}")
                pass
            
            # Check table creation permission
            try:
                cur.execute("""
                    SELECT has_schema_privilege(current_user, 'public', 'CREATE')
                """)
                permissions['create_table'] = cur.fetchone()[0]
            except (psycopg2.Error, Exception) as e:
                logger.debug(f"Could not check create table privilege: {e}")
                pass
            
            # Check basic permissions (we'll test on pg_database which always exists)
            try:
                cur.execute("""
                    SELECT has_table_privilege('pg_database', 'SELECT')
                """)
                permissions['select'] = True
            except (psycopg2.Error, Exception) as e:
                logger.debug(f"Could not check select privilege: {e}")
                pass
        
        return permissions
    
    def _create_database_if_missing(self):
        """Create database if it doesn't exist"""
        # Connect to postgres database to check/create target database
        admin_conn = None
        try:
            admin_conn = psycopg2.connect(
                host=self.parsed_url.hostname,
                port=self.parsed_url.port or 5432,
                database='postgres',  # Connect to default database
                user=self.parsed_url.username,
                password=self.parsed_url.password
            )
            admin_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            with admin_conn.cursor() as cur:
                # Check if database exists
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (self.db_name,)
                )
                
                if not cur.fetchone():
                    # Check permissions
                    permissions = self._check_permissions(admin_conn)
                    
                    if not permissions['create_database']:
                        # Sanitize username for safe logging
                        safe_username = self.parsed_url.username.replace('"', '""') if self.parsed_url.username else 'unknown'
                        safe_db_name = self.db_name.replace('"', '""')
                        
                        logger.error(f"❌ User lacks CREATE DATABASE permission")
                        logger.info("\nTo fix this, run as PostgreSQL superuser:")
                        logger.info(f'  GRANT CREATE ON DATABASE postgres TO "{safe_username}";')
                        logger.info("\nOr create the database manually:")
                        logger.info(f'  CREATE DATABASE "{safe_db_name}";')
                        raise PermissionError("Cannot create database")
                    
                    # Create database using proper SQL identifier
                    logger.info(f"Creating database '{self.db_name}'...")
                    cur.execute(
                        sql.SQL("CREATE DATABASE {}").format(
                            sql.Identifier(self.db_name)
                        )
                    )
                    logger.info(f"✓ Database '{self.db_name}' created")
                else:
                    logger.info(f"✓ Database '{self.db_name}' exists")
                    
        except psycopg2.OperationalError as e:
            if "does not exist" in str(e):
                logger.error(f"❌ Cannot connect to PostgreSQL server")
                logger.info("\nMake sure PostgreSQL is running and accessible")
            else:
                raise
        finally:
            if admin_conn:
                admin_conn.close()
    
    def _setup_connection(self):
        """Setup database connection with auto-creation if needed"""
        if self.auto_setup:
            self._create_database_if_missing()
        
        # Connect to target database
        try:
            self.conn = psycopg2.connect(
                host=self.parsed_url.hostname,
                port=self.parsed_url.port or 5432,
                database=self.db_name,
                user=self.parsed_url.username,
                password=self.parsed_url.password
            )
            logger.info(f"✓ Connected to PostgreSQL: {self.parsed_url.hostname}/{self.db_name}")
            
            # Check permissions in target database
            permissions = self._check_permissions(self.conn)
            
            # Setup pgvector and tables
            self._setup_database_schema(permissions)
            
        except psycopg2.OperationalError as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            logger.info("\nCheck your connection URL and credentials")
            raise
    
    def _setup_database_schema(self, permissions: Dict[str, bool]):
        """Setup pgvector extension and tables"""
        with self.conn.cursor() as cur:
            # Enable pgvector extension
            try:
                # Safe: Extension name is hardcoded and not user-supplied.
                # PostgreSQL does not support parameterization for CREATE EXTENSION.
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                self.conn.commit()
                logger.info("✓ pgvector extension enabled")
            except psycopg2.errors.InsufficientPrivilege:
                logger.warning("⚠️  Cannot create pgvector extension (requires superuser)")
                
                # Check if extension already exists
                cur.execute("""
                    SELECT 1 FROM pg_extension WHERE extname = 'vector'
                """)
                if not cur.fetchone():
                    logger.error("❌ pgvector extension is not installed")
                    logger.info("\nTo install pgvector, run as PostgreSQL superuser:")
                    logger.info(f"  \\c {self.db_name}")
                    logger.info("  CREATE EXTENSION vector;")
                    logger.info("\nOr install system-wide:")
                    logger.info("  sudo apt-get install postgresql-16-pgvector  # Ubuntu/Debian")
                    logger.info("  sudo yum install pgvector  # RHEL/CentOS")
                    logger.info("  brew install pgvector  # macOS")
                    raise
                else:
                    logger.info("✓ pgvector extension already installed")
            except psycopg2.errors.UndefinedFile:
                logger.error("❌ pgvector is not installed on this PostgreSQL server")
                logger.info("\nInstall pgvector:")
                logger.info("  Ubuntu/Debian: sudo apt-get install postgresql-16-pgvector")
                logger.info("  RHEL/CentOS: sudo yum install pgvector")
                logger.info("  macOS: brew install pgvector")
                logger.info("  From source: https://github.com/pgvector/pgvector")
                raise
            
            # Create embeddings table
            if not permissions.get('create_table'):
                logger.warning("⚠️  User lacks CREATE TABLE permission")
                # Check if table exists
                cur.execute("""
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'embeddings'
                """)
                if not cur.fetchone():
                    logger.error("❌ Cannot create embeddings table")
                    logger.info(f"\nGrant permission: GRANT CREATE ON SCHEMA public TO {self.parsed_url.username};")
                    raise PermissionError("Cannot create table")
            
            # Create main embeddings table
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    embedding vector({self.embedding_dim}),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create metadata table for tracking
            cur.execute("""
                CREATE TABLE IF NOT EXISTS embeddings_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            try:
                # Vector similarity index
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_embedding_idx 
                    ON embeddings USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """)
                
                # Metadata index for faster searches
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_metadata_idx 
                    ON embeddings USING GIN (metadata)
                """)
                
                logger.info("✓ Indexes created")
            except psycopg2.errors.InsufficientPrivilege:
                logger.warning("⚠️  Cannot create indexes (performance may be slower)")
            
            self.conn.commit()
            
            # Store metadata
            cur.execute("""
                INSERT INTO embeddings_metadata (key, value) 
                VALUES ('embedding_dim', %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (str(self.embedding_dim),))
            
            cur.execute("""
                INSERT INTO embeddings_metadata (key, value) 
                VALUES ('model', %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (self.embedding_function.__class__.__name__ if self.embedding_function else 'default',))
            
            self.conn.commit()
            logger.info("✓ Database schema ready")
    
    def add_documents(self, documents: List[str], metadatas: List[Dict], ids: List[str]):
        """Add documents with embeddings to PostgreSQL"""
        if not self.embedding_function:
            logger.warning("⚠️  No embedding function provided, storing documents without embeddings")
            embeddings = [[0.0] * self.embedding_dim for _ in documents]
        else:
            logger.info("Generating embeddings...")
            embeddings = self.embedding_function(documents)
        
        with self.conn.cursor() as cur:
            from psycopg2.extras import execute_values

            tuples = [
                (doc_id, doc, json.dumps(meta), embedding)
                for doc, meta, doc_id, embedding in zip(documents, metadatas, ids, embeddings)
            ]
            
            execute_values(cur, 
                """INSERT INTO embeddings (id, content, metadata, embedding) 
                   VALUES %s 
                   ON CONFLICT (id) DO UPDATE 
                   SET content = EXCLUDED.content, 
                       metadata = EXCLUDED.metadata, 
                       embedding = EXCLUDED.embedding""",
                tuples)

            self.conn.commit()
            logger.info(f"✓ Added/updated {len(tuples)} documents")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for similar documents using vector similarity"""
        if not self.embedding_function:
            # Fallback to text search if no embedding function
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, content, metadata, 
                           ts_rank(to_tsvector('english', content), 
                                  plainto_tsquery('english', %s)) as score
                    FROM embeddings
                    WHERE to_tsvector('english', content) @@ plainto_tsquery('english', %s)
                    ORDER BY score DESC
                    LIMIT %s
                """, (query, query, top_k))
                
                results = []
                for row in cur.fetchall():
                    results.append({
                        'content': row['content'],
                        'metadata': row['metadata'] or {},
                        'score': float(row['score']) if row['score'] else 0.0
                    })
                return results
        
        # Generate query embedding
        query_embedding = self.embedding_function([query])[0]
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Vector similarity search
            cur.execute("""
                SELECT id, content, metadata,
                       1 - (embedding <=> %s::vector) as score
                FROM embeddings
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, query_embedding, top_k))
            
            results = []
            for row in cur.fetchall():
                results.append({
                    'content': row['content'],
                    'metadata': row['metadata'] or {},
                    'score': float(row['score'])
                })
            return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {
            'type': 'PostgreSQL + pgvector',
            'database': self.db_name,
            'host': self.parsed_url.hostname
        }
        
        with self.conn.cursor() as cur:
            # Document count
            cur.execute("SELECT COUNT(*) FROM embeddings")
            stats['total_documents'] = cur.fetchone()[0]
            
            # Documents with embeddings
            cur.execute("SELECT COUNT(*) FROM embeddings WHERE embedding IS NOT NULL")
            stats['documents_with_embeddings'] = cur.fetchone()[0]
            
            # Get metadata
            cur.execute("SELECT key, value FROM embeddings_metadata")
            for key, value in cur.fetchall():
                stats[key] = value
            
            # Table size
            cur.execute("""
                SELECT pg_size_pretty(pg_total_relation_size('embeddings'))
            """)
            stats['table_size'] = cur.fetchone()[0]
        
        return stats
    
    def verify_setup(self) -> Dict[str, Any]:
        """Verify database setup and permissions"""
        report = {
            'database': self.db_name,
            'connection': False,
            'permissions': {},
            'schema': {},
            'issues': []
        }
        
        try:
            # Test connection
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
                report['connection'] = True
            
            # Check permissions
            report['permissions'] = self._check_permissions(self.conn)
            
            # Check schema
            with self.conn.cursor() as cur:
                # Check pgvector
                cur.execute("""
                    SELECT 1 FROM pg_extension WHERE extname = 'vector'
                """)
                report['schema']['pgvector'] = bool(cur.fetchone())
                
                # Check tables
                cur.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('embeddings', 'embeddings_metadata')
                """)
                tables = [row[0] for row in cur.fetchall()]
                report['schema']['embeddings_table'] = 'embeddings' in tables
                report['schema']['metadata_table'] = 'embeddings_metadata' in tables
                
                # Check indexes
                cur.execute("""
                    SELECT indexname FROM pg_indexes 
                    WHERE tablename = 'embeddings'
                """)
                indexes = [row[0] for row in cur.fetchall()]
                report['schema']['indexes'] = indexes
            
            # Identify issues
            if not report['schema']['pgvector']:
                report['issues'].append("pgvector extension not installed")
            if not report['schema']['embeddings_table']:
                report['issues'].append("embeddings table missing")
            if not report['permissions']['create_table']:
                report['issues'].append("Cannot create tables")
            
        except Exception as e:
            report['error'] = str(e)
            report['issues'].append(f"Connection error: {e}")
        
        return report
    
    def __del__(self):
        """Clean up connection"""
        if self.conn:
            self.conn.close()

# For backward compatibility with m-bed
PostgreSQLBackend = PostgreSQLEmbeddingsBackend