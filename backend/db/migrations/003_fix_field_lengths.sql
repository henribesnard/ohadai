-- Migration 003: Fix field lengths for long content
-- Date: 2025-11-02
-- Description: Increase varchar length for acte_uniforme, article, and other fields

-- Increase acte_uniforme from VARCHAR(200) to TEXT (unlimited)
ALTER TABLE documents
ALTER COLUMN acte_uniforme TYPE TEXT;

-- Increase article from VARCHAR(20) to VARCHAR(100) for complex article numbers
ALTER TABLE documents
ALTER COLUMN article TYPE VARCHAR(100);

-- Add comment
COMMENT ON COLUMN documents.acte_uniforme IS 'Full text of acte uniforme description (can be very long)';
COMMENT ON COLUMN documents.article IS 'Article number or identifier (can include complex references)';
