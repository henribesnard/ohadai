-- OHADA Expert-Comptable Database Schema
-- PostgreSQL 15+

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- ====================
-- USERS & AUTH
-- ====================

-- Users table (déjà existant, on migre depuis SQLite)
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = TRUE;

-- Revoked tokens
CREATE TABLE IF NOT EXISTS revoked_tokens (
    token_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_jti VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    revoked_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_revoked_tokens_jti ON revoked_tokens(token_jti);
CREATE INDEX idx_revoked_tokens_expires ON revoked_tokens(expires_at);

-- ====================
-- DOCUMENTS (NOUVEAU)
-- ====================

-- Main documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Basic info
    title VARCHAR(500) NOT NULL,
    document_type VARCHAR(50) NOT NULL,  -- 'chapitre', 'acte_uniforme', 'presentation'

    -- Content
    content_text TEXT NOT NULL,
    content_binary BYTEA,  -- Document original (Word/PDF)
    content_hash VARCHAR(64) NOT NULL,  -- SHA-256 for deduplication

    -- OHADA hierarchy (detailed)
    acte_uniforme VARCHAR(200),
    livre INT,
    titre INT,
    partie INT,
    chapitre INT,
    section INT,
    sous_section VARCHAR(10),
    article VARCHAR(50),
    alinea INT,

    -- Parent relationship
    parent_id UUID REFERENCES documents(id) ON DELETE SET NULL,

    -- Flexible metadata (JSONB)
    metadata JSONB DEFAULT '{}',

    -- Tags for search
    tags TEXT[],

    -- Pagination
    page_debut INT,
    page_fin INT,

    -- Versioning
    version INT NOT NULL DEFAULT 1,
    is_latest BOOLEAN DEFAULT TRUE,

    -- Dates
    date_publication DATE,
    date_revision TIMESTAMP,

    -- Status & workflow
    status VARCHAR(20) DEFAULT 'draft',  -- draft, review, published, archived
    validated_by UUID REFERENCES users(user_id),
    validated_at TIMESTAMP,

    -- Audit
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_by UUID REFERENCES users(user_id),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Full-text search
    search_vector tsvector,

    UNIQUE(content_hash, version)
);

-- Indexes for performance
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_partie_chapitre ON documents(partie, chapitre);
CREATE INDEX idx_documents_section ON documents(section) WHERE section IS NOT NULL;
CREATE INDEX idx_documents_article ON documents(article) WHERE article IS NOT NULL;
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_latest ON documents(is_latest) WHERE is_latest = TRUE;
CREATE INDEX idx_documents_metadata ON documents USING GIN(metadata);
CREATE INDEX idx_documents_tags ON documents USING GIN(tags);
CREATE INDEX idx_documents_search ON documents USING GIN(search_vector);
CREATE INDEX idx_documents_parent ON documents(parent_id);
CREATE INDEX idx_documents_hierarchy ON documents(acte_uniforme, partie, chapitre, section);

-- Full-text search trigger
CREATE OR REPLACE FUNCTION documents_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('french', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('french', COALESCE(NEW.content_text, '')), 'B') ||
        setweight(to_tsvector('french', COALESCE(array_to_string(NEW.tags, ' '), '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER documents_search_vector_trigger
BEFORE INSERT OR UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION documents_search_vector_update();

-- Updated timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER documents_updated_at_trigger
BEFORE UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ====================
-- DOCUMENT VERSIONS
-- ====================

CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version INT NOT NULL,

    -- Content snapshot
    content_text TEXT NOT NULL,
    content_binary BYTEA,
    metadata JSONB DEFAULT '{}',

    -- Change tracking
    change_description TEXT,
    changed_by UUID REFERENCES users(user_id),
    changed_at TIMESTAMP DEFAULT NOW(),

    -- Diff (optional)
    diff_from_previous JSONB,

    UNIQUE(document_id, version)
);

CREATE INDEX idx_document_versions_document ON document_versions(document_id);
CREATE INDEX idx_document_versions_changed_at ON document_versions(changed_at DESC);

-- ====================
-- DOCUMENT RELATIONS
-- ====================

CREATE TABLE IF NOT EXISTS document_relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    to_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    relation_type VARCHAR(50) NOT NULL,  -- 'reference', 'replaces', 'complements', 'voir_aussi'
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(from_document_id, to_document_id, relation_type)
);

CREATE INDEX idx_document_relations_from ON document_relations(from_document_id);
CREATE INDEX idx_document_relations_to ON document_relations(to_document_id);
CREATE INDEX idx_document_relations_type ON document_relations(relation_type);

-- ====================
-- DOCUMENT EMBEDDINGS
-- ====================

CREATE TABLE IF NOT EXISTS document_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Chunking info
    chunk_index INT NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_title VARCHAR(255),
    chunk_start_page INT,
    chunk_end_page INT,

    -- Embedding info
    embedding_model VARCHAR(100) NOT NULL,
    chromadb_id VARCHAR(255) NOT NULL,  -- ID in ChromaDB
    chromadb_collection VARCHAR(100) NOT NULL,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(document_id, chunk_index, embedding_model)
);

CREATE INDEX idx_document_embeddings_document ON document_embeddings(document_id);
CREATE INDEX idx_document_embeddings_chromadb ON document_embeddings(chromadb_id);
CREATE INDEX idx_document_embeddings_collection ON document_embeddings(chromadb_collection);

-- ====================
-- CONVERSATIONS
-- ====================

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_updated ON conversations(updated_at DESC);

CREATE TRIGGER conversations_updated_at_trigger
BEFORE UPDATE ON conversations
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ====================
-- MESSAGES
-- ====================

CREATE TABLE IF NOT EXISTS messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    content TEXT NOT NULL,
    is_user BOOLEAN NOT NULL,

    -- Metadata (sources, performance, etc.)
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_user ON messages(user_id);
CREATE INDEX idx_messages_created ON messages(created_at DESC);

-- ====================
-- FEEDBACK
-- ====================

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(message_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    rating INT CHECK (rating >= 1 AND rating <= 5),
    feedback_type VARCHAR(50),  -- 'helpful', 'not_helpful', 'inaccurate', 'incomplete'
    comment TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_feedback_conversation ON feedback(conversation_id);
CREATE INDEX idx_feedback_message ON feedback(message_id);
CREATE INDEX idx_feedback_user ON feedback(user_id);

-- ====================
-- AUDIT LOGS
-- ====================

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL,  -- 'document', 'user', 'conversation'
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,  -- 'created', 'updated', 'deleted', 'viewed', 'downloaded'
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

-- ====================
-- API USAGE TRACKING
-- ====================

CREATE TABLE IF NOT EXISTS api_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    endpoint VARCHAR(200) NOT NULL,
    method VARCHAR(10) NOT NULL,

    -- LLM usage
    provider VARCHAR(50),  -- 'openai', 'deepseek'
    model VARCHAR(100),
    tokens_input INT,
    tokens_output INT,
    cost_usd DECIMAL(10, 6),

    -- Performance
    duration_ms INT,
    status_code INT,

    -- Cache
    cache_hit BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_api_usage_user ON api_usage(user_id);
CREATE INDEX idx_api_usage_endpoint ON api_usage(endpoint);
CREATE INDEX idx_api_usage_created ON api_usage(created_at DESC);
CREATE INDEX idx_api_usage_provider ON api_usage(provider);

-- ====================
-- VIEWS
-- ====================

-- View for active documents with full hierarchy
CREATE OR REPLACE VIEW v_documents_active AS
SELECT
    d.*,
    CONCAT_WS(' > ',
        d.acte_uniforme,
        CASE WHEN d.livre IS NOT NULL THEN 'Livre ' || d.livre END,
        CASE WHEN d.titre IS NOT NULL THEN 'Titre ' || d.titre END,
        CASE WHEN d.partie IS NOT NULL THEN 'Partie ' || d.partie END,
        CASE WHEN d.chapitre IS NOT NULL THEN 'Chapitre ' || d.chapitre END,
        CASE WHEN d.section IS NOT NULL THEN 'Section ' || d.section END,
        CASE WHEN d.sous_section IS NOT NULL THEN 'Sous-section ' || d.sous_section END,
        CASE WHEN d.article IS NOT NULL THEN 'Article ' || d.article END
    ) as hierarchy_display,
    CONCAT_WS(', ',
        CASE WHEN d.article IS NOT NULL THEN 'Article ' || d.article END,
        CASE WHEN d.section IS NOT NULL THEN 'Section ' || d.section || COALESCE(d.sous_section, '') END,
        CASE WHEN d.chapitre IS NOT NULL THEN 'Chapitre ' || d.chapitre END,
        CASE WHEN d.partie IS NOT NULL THEN 'Partie ' || d.partie END,
        d.acte_uniforme,
        CASE WHEN d.date_revision IS NOT NULL THEN 'SYSCOHADA Révisé ' || EXTRACT(YEAR FROM d.date_revision) END
    ) as citation
FROM documents d
WHERE d.status = 'published' AND d.is_latest = TRUE;

-- View for document statistics
CREATE OR REPLACE VIEW v_document_stats AS
SELECT
    document_type,
    COUNT(*) as total_count,
    COUNT(CASE WHEN status = 'published' THEN 1 END) as published_count,
    COUNT(CASE WHEN status = 'draft' THEN 1 END) as draft_count,
    AVG(version) as avg_version
FROM documents
WHERE is_latest = TRUE
GROUP BY document_type;

-- ====================
-- FUNCTIONS
-- ====================

-- Function to create a new document version
CREATE OR REPLACE FUNCTION create_document_version()
RETURNS TRIGGER AS $$
BEGIN
    -- If document is being updated, save previous version
    IF TG_OP = 'UPDATE' AND OLD.content_text != NEW.content_text THEN
        INSERT INTO document_versions (
            document_id,
            version,
            content_text,
            content_binary,
            metadata,
            change_description,
            changed_by,
            changed_at
        ) VALUES (
            OLD.id,
            OLD.version,
            OLD.content_text,
            OLD.content_binary,
            OLD.metadata,
            'Updated to version ' || NEW.version,
            NEW.updated_by,
            NOW()
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER document_version_trigger
BEFORE UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION create_document_version();

-- Function to search documents by hierarchy
CREATE OR REPLACE FUNCTION search_documents_by_hierarchy(
    p_acte_uniforme VARCHAR DEFAULT NULL,
    p_partie INT DEFAULT NULL,
    p_chapitre INT DEFAULT NULL,
    p_section INT DEFAULT NULL,
    p_article VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    title VARCHAR,
    hierarchy_display TEXT,
    citation TEXT,
    relevance FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.title,
        v.hierarchy_display,
        v.citation,
        1.0::FLOAT as relevance
    FROM documents d
    JOIN v_documents_active v ON v.id = d.id
    WHERE
        (p_acte_uniforme IS NULL OR d.acte_uniforme ILIKE '%' || p_acte_uniforme || '%') AND
        (p_partie IS NULL OR d.partie = p_partie) AND
        (p_chapitre IS NULL OR d.chapitre = p_chapitre) AND
        (p_section IS NULL OR d.section = p_section) AND
        (p_article IS NULL OR d.article = p_article)
    ORDER BY d.partie, d.chapitre, d.section, d.article;
END;
$$ LANGUAGE plpgsql;

-- ====================
-- SEED DATA
-- ====================

-- Insert default admin user (password: admin123 - CHANGE IN PRODUCTION!)
-- Hash generated with: bcrypt.hashpw(b"admin123", bcrypt.gensalt())
INSERT INTO users (email, password_hash, full_name, is_admin, is_active)
VALUES (
    'admin@ohada.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7TUU4YLJ.O',  -- admin123
    'Administrateur OHADA',
    TRUE,
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- Create comment
COMMENT ON TABLE documents IS 'Main table for OHADA documents with full hierarchy support';
COMMENT ON TABLE document_embeddings IS 'Links documents to their embeddings in ChromaDB';
COMMENT ON TABLE document_versions IS 'Version history for all documents';
COMMENT ON TABLE audit_logs IS 'Audit trail for all system actions';
