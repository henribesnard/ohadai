-- Migration: Add collection and sub_collection fields for organizational hierarchy
-- Date: 2025-01-02
-- Description: Adds fields to capture the directory structure (actes_uniformes, plan_comptable, etc.)

-- Add new columns to documents table
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS collection VARCHAR(100),
ADD COLUMN IF NOT EXISTS sub_collection VARCHAR(200);

-- Add comments
COMMENT ON COLUMN documents.collection IS 'Main category: actes_uniformes, plan_comptable, presentation_ohada, etc.';
COMMENT ON COLUMN documents.sub_collection IS 'Subcategory: specific acte uniforme name, partie number, etc.';

-- Create indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection);
CREATE INDEX IF NOT EXISTS idx_documents_sub_collection ON documents(sub_collection);
CREATE INDEX IF NOT EXISTS idx_documents_collection_sub ON documents(collection, sub_collection);

-- Update search vector trigger to include collection fields
CREATE OR REPLACE FUNCTION documents_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('french', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('french', COALESCE(NEW.content_text, '')), 'B') ||
        setweight(to_tsvector('french', COALESCE(array_to_string(NEW.tags, ' '), '')), 'C') ||
        setweight(to_tsvector('french', COALESCE(NEW.collection, '')), 'D') ||
        setweight(to_tsvector('french', COALESCE(NEW.sub_collection, '')), 'D');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Update the view to include collection fields
DROP VIEW IF EXISTS v_documents_active;
CREATE OR REPLACE VIEW v_documents_active AS
SELECT
    d.*,
    -- Collection hierarchy display
    CONCAT_WS(' > ',
        d.collection,
        d.sub_collection
    ) as collection_display,
    -- OHADA hierarchy display
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
    -- Full display (collection + hierarchy)
    CONCAT_WS(' > ',
        d.collection,
        d.sub_collection,
        CASE WHEN d.partie IS NOT NULL THEN 'Partie ' || d.partie END,
        CASE WHEN d.chapitre IS NOT NULL THEN 'Chapitre ' || d.chapitre END,
        CASE WHEN d.section IS NOT NULL THEN 'Section ' || d.section END,
        CASE WHEN d.article IS NOT NULL THEN 'Article ' || d.article END
    ) as full_hierarchy_display,
    -- Citation
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

-- Add to document_stats view
DROP VIEW IF EXISTS v_document_stats;
CREATE OR REPLACE VIEW v_document_stats AS
SELECT
    document_type,
    collection,
    sub_collection,
    COUNT(*) as total_count,
    COUNT(CASE WHEN status = 'published' THEN 1 END) as published_count,
    COUNT(CASE WHEN status = 'draft' THEN 1 END) as draft_count,
    AVG(version) as avg_version
FROM documents
WHERE is_latest = TRUE
GROUP BY document_type, collection, sub_collection;

-- Migration complete
COMMENT ON TABLE documents IS 'Main table for OHADA documents with organizational (collection) and OHADA (partie/chapitre) hierarchy support';
