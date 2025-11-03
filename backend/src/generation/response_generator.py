"""
Module de génération de réponses pour le système OHADA Expert-Comptable.
Responsable de l'analyse du contexte et de la génération des réponses finales.
"""

import logging

# Configuration du logging
logger = logging.getLogger("ohada_response_generator")

class ResponseGenerator:
    """Générateur de réponses pour les requêtes OHADA"""
    
    def __init__(self, llm_client):
        """
        Initialise le générateur de réponses
        
        Args:
            llm_client: Client LLM pour la génération de texte
        """
        self.llm_client = llm_client
    
    def generate_response(self, query: str, context: str) -> str:
        """
        Génère une réponse en UNE SEULE étape (optimisation).

        ANCIENNE MÉTHODE (2 étapes, ~1800-3200ms):
        - Étape 1: Analyse du contexte (800 tokens, ~800-1200ms)
        - Étape 2: Génération réponse (1200 tokens, ~1000-2000ms)

        NOUVELLE MÉTHODE (1 étape, ~1000-2000ms):
        - Prompt unifié avec instructions d'analyse intégrées
        - Économie de ~800-1200ms et d'un appel réseau

        Args:
            query: Requête de l'utilisateur
            context: Contexte pertinent

        Returns:
            Réponse générée
        """
        # Si le contexte est vide ou trop court, réponse basée sur les connaissances générales
        if not context or len(context) < 500:
            unified_prompt = f"""
Question: {query}

En tant qu'expert-comptable OHADA, répondez à cette question de manière structurée:

Instructions:
1. Identifiez le sujet principal de la question
2. Fournissez une réponse claire et pédagogique
3. Utilisez votre expertise du plan comptable OHADA
4. Structurez votre réponse avec des paragraphes clairs

IMPORTANT:
- N'utilisez PAS de notation mathématique LaTeX ou formules entre crochets
- Écrivez les formules en texte simple: "Montant = Base × Taux" ou "A / B"

Réponse:
            """

            try:
                return self.llm_client.generate_response(
                    system_prompt="Vous êtes un expert-comptable OHADA. Répondez de façon claire et structurée.",
                    user_prompt=unified_prompt,
                    max_tokens=1500,  # Légèrement augmenté pour compenser
                    temperature=0.4
                )
            except Exception as e:
                logger.error(f"Erreur lors de la génération de réponse: {e}")
                return "Désolé, je n'ai pas pu trouver d'informations sur cette question dans ma base de connaissances OHADA."

        # OPTIMISATION: Génération en UNE étape au lieu de DEUX
        # Prompt unifié qui intègre analyse + génération
        unified_prompt = f"""
Vous êtes un expert-comptable OHADA. Analysez le contexte fourni et répondez à la question de manière structurée.

CONTEXTE DISPONIBLE:
{context}

QUESTION:
{query}

INSTRUCTIONS:
1. Analysez le contexte pour identifier les informations pertinentes
2. Repérez les concepts clés, règles et procédures comptables applicables
3. Structurez votre réponse de façon claire et pédagogique
4. Citez les articles/comptes/sections pertinents si présents dans le contexte
5. Soyez précis et concis

CONTRAINTES DE FORMATAGE:
- N'utilisez PAS de notation mathématique LaTeX (pas de \\frac, \\times, etc.)
- N'utilisez PAS de formules entre crochets
- Écrivez les formules en texte simple: "Montant = Base × Taux"
- Pour les fractions: "A divisé par B" ou "A / B"
- Utilisez des listes à puces si nécessaire pour la clarté

Réponse:
        """

        try:
            logger.info("Génération de réponse en une seule étape (optimisée)")
            answer = self.llm_client.generate_response(
                system_prompt="Vous êtes un expert-comptable OHADA. Analysez et répondez en une seule étape.",
                user_prompt=unified_prompt,
                max_tokens=1500,  # Légèrement augmenté pour compenser l'analyse intégrée
                temperature=0.4   # Compromis entre précision et fluidité
            )

            return answer

        except Exception as e:
            logger.error(f"Erreur lors de la génération de réponse: {e}")

            # Fallback: génération simplifiée
            fallback_prompt = f"""
Question: {query}

Contexte:
{context}

Répondez de manière claire et structurée en vous basant sur le contexte fourni.
            """

            try:
                logger.info("Génération de réponse (fallback)")
                return self.llm_client.generate_response(
                    system_prompt="Vous êtes un expert-comptable OHADA.",
                    user_prompt=fallback_prompt,
                    max_tokens=1500,
                    temperature=0.4
                )
            except Exception as e:
                logger.error(f"Erreur lors de la génération de réponse (fallback): {e}")
                return "Désolé, je n'ai pas pu générer une réponse. Veuillez réessayer ou reformuler votre question."