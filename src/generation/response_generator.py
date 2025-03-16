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
        Analyse le contexte et génère une réponse en deux étapes
        
        Args:
            query: Requête de l'utilisateur
            context: Contexte pertinent
            
        Returns:
            Réponse générée
        """
        # Si le contexte est vide ou trop court, on passe directement à la génération de réponse
        if not context or len(context) < 500:
            direct_prompt = f"""
            Question: {query}
            
            En tant qu'expert-comptable spécialisé dans le plan comptable OHADA, veuillez répondre 
        à cette question de manière claire et précise, en vous basant sur vos connaissances
        du plan comptable OHADA. Soyez pédagogique et structuré dans votre réponse.
        
        IMPORTANT: N'utilisez pas de notation mathématique complexe ou de formules entre crochets.
        Écrivez toutes les formules en texte simple, par exemple "Montant = Base * Taux" ou "A / B".
            """
            
            try:
                return self.llm_client.generate_response(
                    system_prompt="Vous êtes un expert-comptable spécialisé dans le plan comptable OHADA. N'utilisez jamais de notation mathématique LaTeX ou de formules entre crochets.",
                    user_prompt=direct_prompt,
                    max_tokens=1200,
                    temperature=0.3
                )
            except Exception as e:
                logger.error(f"Erreur lors de la génération de réponse directe: {e}")
                return "Désolé, je n'ai pas pu trouver d'informations sur cette question dans ma base de connaissances OHADA."
        
        # Étape 1: Analyse du contexte pour extraire les informations pertinentes
        analysis_prompt = f"""
        Vous êtes un expert-comptable spécialisé dans le plan comptable OHADA.
        
        Analysez d'abord le contexte suivant pour extraire les informations pertinentes à la question posée.
        Identifiez les concepts clés, les règles et les procédures comptables qui s'appliquent.
        
        Question: {query}
        
        Contexte:
        {context}
        
        Votre analyse:
        """
        
        try:
            # Génération de l'analyse
            logger.info("Génération de l'analyse du contexte")
            analysis = self.llm_client.generate_response(
                system_prompt="Analysez le contexte et extrayez les informations pertinentes pour répondre à la question.",
                user_prompt=analysis_prompt,
                max_tokens=800,
                temperature=0.3
            )
            
            # Étape 2: Génération de la réponse basée sur l'analyse
            answer_prompt = f"""
            Vous êtes un expert-comptable spécialisé dans le plan comptable OHADA.
            
            Voici votre analyse des informations disponibles sur la question:
            {analysis}
            
            Maintenant, répondez à la question de manière claire, précise et structurée:
            {query}
            
            IMPORTANT: 
        - N'utilisez PAS de notation mathématique complexe ou de formules entre crochets.
        - Écrivez toutes les formules en texte simple (par exemple "Montant = Base × Taux").
        - Pour les fractions, écrivez-les sous forme de division (par exemple "A divisé par B" ou "A / B").

            Votre réponse:
            """
            
            # Génération de la réponse finale
            logger.info("Génération de la réponse finale")
            answer = self.llm_client.generate_response(
                system_prompt="Répondez à la question de façon claire et précise en vous basant sur votre analyse. N'utilisez jamais de notation mathématique LaTeX ou de formules entre crochets.",
                user_prompt=answer_prompt,
                max_tokens=1200,
                temperature=0.5  # Légèrement plus créatif pour la réponse finale
            )
            
            return answer
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse et génération de réponse: {e}")
            
            # Fallback: génération directe sans analyse préalable
            direct_prompt = f"""
            Question: {query}
            
            Contexte:
            {context}
            
            Répondez à la question de manière claire et précise en vous basant sur le contexte fourni.
            """
            
            try:
                logger.info("Génération de réponse directe (fallback)")
                return self.llm_client.generate_response(
                    system_prompt="Vous êtes un expert-comptable spécialisé dans le plan comptable OHADA.",
                    user_prompt=direct_prompt,
                    max_tokens=1200,
                    temperature=0.3
                )
            except Exception as e:
                logger.error(f"Erreur lors de la génération de réponse directe: {e}")
                return "Désolé, je n'ai pas pu générer une réponse. Veuillez réessayer ou reformuler votre question."