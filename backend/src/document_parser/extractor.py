"""
Hierarchy extraction utilities for OHADA documents
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class HierarchyInfo:
    """Extracted hierarchy information"""
    acte_uniforme: Optional[str] = None
    livre: Optional[int] = None
    titre: Optional[int] = None
    partie: Optional[int] = None
    chapitre: Optional[int] = None
    section: Optional[int] = None
    sous_section: Optional[str] = None
    article: Optional[str] = None
    alinea: Optional[int] = None


class HierarchyExtractor:
    """Extract OHADA hierarchy elements from document text"""

    # Regex patterns for hierarchy elements
    PATTERNS = {
        'acte_uniforme': r'Acte [Uu]niforme\s+(?:portant|relatif|sur)\s+(.+?)(?:\n|$|\.)',
        'livre': r'LIVRE\s+([IVXLCDM]+|[0-9]+)[:\s\-]',
        'titre': r'TITRE\s+([IVXLCDM]+|[0-9]+)[:\s\-]',
        'partie': r'(?:PARTIE|Partie)\s+([IVXLCDM]+|[0-9]+)[:\s\-]',
        'chapitre': r'(?:CHAPITRE|Chapitre)\s+([IVXLCDM]+|[0-9]+)[:\s\-]',
        'section': r'Section\s+([IVXLCDM]+|[0-9]+)[:\s\-]',
        'sous_section': r'Sous[- ]section\s+([IVXLCDM]+|[0-9]+[A-Z]?)[:\s\-]',
        'article': r'Article\s+([0-9]+(?:-[0-9]+)?(?:\s+[a-z]+)?)',
        'alinea': r'(?:Alinéa|Al\.)\s+([0-9]+)'
    }

    @staticmethod
    def roman_to_int(roman: str) -> int:
        """Convert Roman numeral to integer"""
        roman_values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
        result = 0
        prev_value = 0

        for char in reversed(roman.upper()):
            value = roman_values.get(char, 0)
            if value < prev_value:
                result -= value
            else:
                result += value
            prev_value = value

        return result

    @classmethod
    def extract_number(cls, text: str) -> Optional[int]:
        """Extract number from text (handles both Roman and Arabic numerals)"""
        text = text.strip()

        # Try Roman numeral first
        if re.match(r'^[IVXLCDM]+$', text, re.IGNORECASE):
            return cls.roman_to_int(text)

        # Try Arabic numeral
        match = re.search(r'(\d+)', text)
        if match:
            return int(match.group(1))

        return None

    @classmethod
    def extract_hierarchy_from_text(cls, text: str, title: str = "") -> HierarchyInfo:
        """
        Extract hierarchy information from document text and title

        Args:
            text: Full document text
            title: Document title

        Returns:
            HierarchyInfo object with extracted hierarchy
        """
        hierarchy = HierarchyInfo()

        # Combine title and first 2000 chars for analysis
        analysis_text = f"{title}\n{text[:2000]}"

        # Extract acte uniforme
        match = re.search(cls.PATTERNS['acte_uniforme'], analysis_text, re.IGNORECASE)
        if match:
            hierarchy.acte_uniforme = match.group(1).strip()

        # Extract livre
        match = re.search(cls.PATTERNS['livre'], analysis_text, re.IGNORECASE)
        if match:
            hierarchy.livre = cls.extract_number(match.group(1))

        # Extract titre
        match = re.search(cls.PATTERNS['titre'], analysis_text, re.IGNORECASE)
        if match:
            hierarchy.titre = cls.extract_number(match.group(1))

        # Extract partie
        match = re.search(cls.PATTERNS['partie'], analysis_text, re.IGNORECASE)
        if match:
            hierarchy.partie = cls.extract_number(match.group(1))

        # Extract chapitre
        match = re.search(cls.PATTERNS['chapitre'], analysis_text, re.IGNORECASE)
        if match:
            hierarchy.chapitre = cls.extract_number(match.group(1))

        # Extract section
        match = re.search(cls.PATTERNS['section'], analysis_text, re.IGNORECASE)
        if match:
            hierarchy.section = cls.extract_number(match.group(1))

        # Extract sous-section
        match = re.search(cls.PATTERNS['sous_section'], analysis_text, re.IGNORECASE)
        if match:
            hierarchy.sous_section = match.group(1).strip()

        # Extract article
        match = re.search(cls.PATTERNS['article'], analysis_text, re.IGNORECASE)
        if match:
            hierarchy.article = match.group(1).strip()

        # Extract alinéa
        match = re.search(cls.PATTERNS['alinea'], analysis_text, re.IGNORECASE)
        if match:
            hierarchy.alinea = int(match.group(1))

        return hierarchy

    @staticmethod
    def extract_document_type(text: str, title: str = "") -> str:
        """
        Determine document type based on content

        Returns: 'acte_uniforme', 'chapitre', 'article', 'presentation', 'other'
        """
        combined = f"{title}\n{text[:500]}".lower()

        if 'acte uniforme' in combined:
            return 'acte_uniforme'
        elif re.search(r'chapitre\s+[0-9ivxlcdm]+', combined, re.IGNORECASE):
            return 'chapitre'
        elif re.search(r'article\s+[0-9]+', combined, re.IGNORECASE):
            return 'article'
        elif any(word in combined for word in ['présentation', 'introduction', 'préambule']):
            return 'presentation'
        else:
            return 'other'

    @staticmethod
    def extract_tags(text: str) -> List[str]:
        """
        Extract relevant tags from document text

        Returns: List of tags (normalized, lowercase)
        """
        tags = set()

        # Legal terms
        legal_terms = [
            'comptabilité', 'audit', 'société', 'entreprise', 'fiscal',
            'commercial', 'droit', 'obligation', 'responsabilité',
            'capital', 'associé', 'gérant', 'conseil', 'assemblée',
            'bilan', 'compte', 'état financier', 'consolidation',
            'commissaire aux comptes', 'rapport', 'certification'
        ]

        text_lower = text.lower()
        for term in legal_terms:
            if term in text_lower:
                tags.add(term)

        # Extract document-specific tags from title patterns
        if 'syscohada' in text_lower:
            tags.add('syscohada')
        if 'révisé' in text_lower:
            tags.add('révisé')
        if 'ohada' in text_lower:
            tags.add('ohada')

        return sorted(list(tags))

    @staticmethod
    def extract_references(text: str) -> List[Dict[str, str]]:
        """
        Extract cross-references to other articles/sections

        Returns: List of references with type and identifier
        """
        references = []

        # Article references
        article_refs = re.finditer(
            r'(?:voir|cf\.|conformément à|selon)\s+(?:l\')?[Aa]rticle\s+([0-9]+(?:-[0-9]+)?)',
            text,
            re.IGNORECASE
        )
        for match in article_refs:
            references.append({
                'type': 'article',
                'identifier': match.group(1),
                'context': match.group(0)
            })

        # Section references
        section_refs = re.finditer(
            r'(?:voir|cf\.|conformément à|selon)\s+(?:la\s+)?Section\s+([IVXLCDM]+|[0-9]+)',
            text,
            re.IGNORECASE
        )
        for match in section_refs:
            references.append({
                'type': 'section',
                'identifier': match.group(1),
                'context': match.group(0)
            })

        return references

    @staticmethod
    def extract_date_publication(text: str, title: str = "") -> Optional[str]:
        """
        Extract publication date from document

        Returns: ISO date string (YYYY-MM-DD) or None
        """
        combined = f"{title}\n{text[:1000]}"

        # Look for dates in various formats
        date_patterns = [
            r'(\d{1,2})\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})',
            r'(\d{4})-(\d{2})-(\d{2})',
            r'(\d{2})/(\d{2})/(\d{4})'
        ]

        months = {
            'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
            'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
            'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
        }

        # French date format
        match = re.search(date_patterns[0], combined, re.IGNORECASE)
        if match:
            day = match.group(1).zfill(2)
            month_name = match.group(2).lower()
            year = match.group(3)
            month = months.get(month_name, '01')
            return f"{year}-{month}-{day}"

        # ISO format
        match = re.search(date_patterns[1], combined)
        if match:
            return match.group(0)

        # DD/MM/YYYY format
        match = re.search(date_patterns[2], combined)
        if match:
            day, month, year = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        return None
