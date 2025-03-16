"""
Interface Streamlit pour l'assistant OHADA AI Expert-Comptable avec streaming
Version design moderne inspiré de Perplexity avec support de streaming des réponses
"""

import streamlit as st
import asyncio
import time
from dotenv import load_dotenv
import aiohttp
import json
from utils.ohada_utils import format_time
from utils.ohada_streaming import StreamingLLMClient, generate_streaming_response
from retrieval.ohada_hybrid_retriever import create_ohada_query_api

# Chargement des variables d'environnement
load_dotenv()

# Configuration de la page Streamlit
st.set_page_config(
    page_title="OHAD'AI Expert-Comptable",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styles CSS personnalisés inspirés de Perplexity
st.markdown("""
<style>
    /* Couleurs et styles généraux */
    :root {
        --primary: #0e766e;
        --light-bg: #f9f9f9;
        --text: #1e293b;
        --subtle-text: #64748b;
        --border: #e2e8f0;
    }
    
    /* En-tête principal */
    .main-header {
        font-size: 2.2rem;
        color: var(--text);
        font-weight: 600;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
    }
    
    .main-header img {
        height: 32px;
        margin-right: 10px;
    }
    
    /* Carte de recherche */
    .search-card {
        background-color: white;
        border-radius: 10px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        border: 1px solid var(--border);
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* Bouton de recherche */
    .search-button {
        background-color: var(--primary);
        color: white;
        padding: 8px 16px;
        border-radius: 5px;
        font-weight: 500;
        border: none;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }
    
    /* Boîte de réponse */
    .answer-container {
        background-color: white;
        border-radius: 10px;
        padding: 2rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
        border: 1px solid var(--border);
    }
    
    /* Sources */
    .source-card {
        background-color: var(--light-bg);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid var(--border);
    }
    
    .source-title {
        font-weight: 600;
        color: var(--text);
        margin-bottom: 0.5rem;
    }
    
    .source-meta {
        font-size: 0.85rem;
        color: var(--subtle-text);
        margin-bottom: 0.5rem;
    }
    
    .source-preview {
        font-size: 0.95rem;
        color: var(--text);
        line-height: 1.5;
    }
    
    /* Navigation latérale */
    .sidebar .sidebar-content {
        background-color: white;
        border-right: 1px solid var(--border);
    }
    
    /* Masquer les éléments Streamlit par défaut */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* Style du texte d'entrée */
    .stTextArea textarea {
        border-radius: 8px;
        border: 1px solid var(--border);
        padding: 10px;
        font-size: 1rem;
    }
    
    /* Style des boutons */
    .stButton > button {
        background-color: var(--primary);
        color: white;
        border-radius: 5px;
        border: none;
        padding: 8px 16px;
        font-weight: 500;
    }
    
    /* Exemples de questions */
    .example-question {
        display: inline-block;
        background-color: var(--light-bg);
        padding: 6px 12px;
        margin: 5px;
        border-radius: 16px;
        font-size: 0.9rem;
        color: var(--text);
        cursor: pointer;
        border: 1px solid var(--border);
    }
    
    /* Séparateur */
    hr {
        margin: 1.5rem 0;
        border: 0;
        border-top: 1px solid var(--border);
    }
    
    /* Barre de progression */
    .progress-container {
        width: 100%;
        background-color: var(--light-bg);
        border-radius: 4px;
        margin: 10px 0;
        height: 8px;
        overflow: hidden;
    }
    
    .progress-bar {
        height: 100%;
        background-color: var(--primary);
        border-radius: 4px;
        transition: width 0.3s ease;
    }
    
    /* Indicateur d'étape */
    .step-indicator {
        display: flex;
        justify-content: space-between;
        margin-bottom: 10px;
        font-size: 0.8rem;
        color: var(--subtle-text);
    }
    
    .step {
        display: flex;
        align-items: center;
    }
    
    .step.active {
        color: var(--primary);
        font-weight: 500;
    }
    
    .step-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: var(--light-bg);
        margin-right: 5px;
    }
    
    .step.active .step-dot {
        background-color: var(--primary);
    }
</style>
""", unsafe_allow_html=True)

# Créer un espace réservé pour afficher la réponse en streaming
def create_streaming_response_placeholder():
    """Crée un conteneur pour afficher la réponse en streaming"""
    response_placeholder = st.empty()
    response_placeholder.markdown(
        '<div class="answer-container"><p>Préparation de la réponse...</p></div>',
        unsafe_allow_html=True
    )
    return response_placeholder

# Fonction pour afficher la progression
def update_progress(progress_placeholder, percentage, status="En cours"):
    """Met à jour la barre de progression"""
    steps = [
        {"name": "Recherche", "active": status == "retrieving"},
        {"name": "Analyse", "active": status == "analyzing"},
        {"name": "Génération", "active": status == "generating"},
        {"name": "Terminé", "active": status == "complete"}
    ]
    
    # Créer les indicateurs d'étape
    step_html = '<div class="step-indicator">'
    for step in steps:
        step_class = "step active" if step["active"] else "step"
        step_html += f'<div class="{step_class}"><div class="step-dot"></div>{step["name"]}</div>'
    step_html += '</div>'
    
    # Créer la barre de progression
    progress_html = f"""
    <div class="progress-container">
        <div class="progress-bar" style="width: {percentage}%;"></div>
    </div>
    <div style="text-align: center; font-size: 0.8rem; color: var(--subtle-text);">{status.capitalize()} - {percentage:.0f}%</div>
    {step_html}
    """
    
    progress_placeholder.markdown(progress_html, unsafe_allow_html=True)

# Version asynchrone de la génération de réponse en streaming
async def generate_streaming_answer(retriever, query, n_results, include_sources, response_placeholder, progress_placeholder):
    """Génère une réponse en streaming directement dans l'interface Streamlit"""
    # Initialiser la progression
    update_progress(progress_placeholder, 0, "Démarrage")
    
    # Étape 1: Reformulation de la requête
    update_progress(progress_placeholder, 10, "Reformulation")
    # CORRECTION: utiliser query_reformulator au lieu de reformulate_query
    reformulated_query = retriever.query_reformulator.reformulate(query)
    
    # Étape 2: Recherche hybride
    update_progress(progress_placeholder, 20, "retrieving")
    search_results = retriever.search_hybrid(
        query=reformulated_query,
        n_results=n_results,
        rerank=True
    )
    
    # Étape 3: Résumé du contexte
    update_progress(progress_placeholder, 40, "analyzing")
    # CORRECTION: utiliser context_processor au lieu de summarize_context
    context = retriever.context_processor.summarize_context(
        query=reformulated_query,
        search_results=search_results
    )
    
    # Étape 4: Génération de la réponse en streaming
    update_progress(progress_placeholder, 50, "generating")
    
    # Initialiser le client de streaming
    streaming_client = StreamingLLMClient(retriever.llm_config)
    
    # Système de prompt et prompt utilisateur
    system_prompt = "Vous êtes un expert-comptable spécialisé dans le plan comptable OHADA. N'utilisez jamais de notation mathématique LaTeX ou de formules entre crochets."
    user_prompt = f"""
    Question: {query}
    
    Contexte:
    {context}
    
    Répondez à la question de manière claire, précise et structurée en vous basant sur le contexte fourni.
    """
    
    # Générer la réponse en streaming avec mise à jour progressive
    response_text = ""
    progress_value = 50  # Commencer à 50% après la recherche et l'analyse
    
    async for chunk in generate_streaming_response(streaming_client, system_prompt, user_prompt):
        response_text += chunk
        
        # Mettre à jour le contenu de la réponse
        response_placeholder.markdown(
            f'<div class="answer-container">{response_text}</div>',
            unsafe_allow_html=True
        )
        
        # Mettre à jour la progression (de 50% à 95%)
        progress_value += 0.5
        if progress_value > 95:
            progress_value = 95
        
        update_progress(progress_placeholder, progress_value, "generating")
        
        # Petite pause pour rendre le streaming plus visible
        await asyncio.sleep(0.01)
    
    # Finaliser la progression
    update_progress(progress_placeholder, 100, "complete")
    
    # Préparer les sources pour l'affichage
    sources = []
    if include_sources:
        # CORRECTION: utiliser context_processor pour préparer les sources
        sources = retriever.context_processor.prepare_sources(search_results)
    
    return response_text, sources

# Version en streaming direct depuis le serveur FastAPI (si déployé)
async def stream_from_api(query, n_results, include_sources, response_placeholder, progress_placeholder):
    """Effectue une requête en streaming vers le serveur API FastAPI"""
    API_URL = "http://localhost:8080/stream"  # Ajustez selon votre configuration
    
    # Préparer les paramètres de la requête
    params = {
        "query": query,
        "n_results": n_results,
        "include_sources": "true" if include_sources else "false"
    }
    
    try:
        # Initialiser la progression
        update_progress(progress_placeholder, 0, "Connexion")
        
        # Établir la connexion SSE
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    response_placeholder.error(f"Erreur du serveur: {error_text}")
                    return None, None
                
                # Variables pour collecter les données
                response_text = ""
                sources = None
                response_id = None
                
                # Lire le flux d'événements
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if not line:
                        continue
                    
                    if line.startswith('event:'):
                        event_type = line.split(':', 1)[1].strip()
                        continue
                    
                    if line.startswith('data:'):
                        data_json = line.split(':', 1)[1].strip()
                        data = json.loads(data_json)
                        
                        if event_type == 'start':
                            response_id = data.get('id')
                            update_progress(progress_placeholder, 5, "Démarrage")
                            
                        elif event_type == 'progress':
                            completion = data.get('completion', 0) * 100
                            status = data.get('status', 'en cours')
                            update_progress(progress_placeholder, completion, status)
                            
                        elif event_type == 'chunk':
                            # Ajouter le morceau au texte de réponse
                            chunk = data.get('text', '')
                            response_text += chunk
                            
                            # Mettre à jour l'affichage
                            response_placeholder.markdown(
                                f'<div class="answer-container">{response_text}</div>',
                                unsafe_allow_html=True
                            )
                            
                            # Mettre à jour la progression
                            completion = data.get('completion', 0) * 100
                            update_progress(progress_placeholder, completion, "generating")
                            
                        elif event_type == 'complete':
                            # Finaliser la réponse
                            response_text = data.get('answer', response_text)
                            sources = data.get('sources')
                            
                            # Mettre à jour pour la dernière fois
                            response_placeholder.markdown(
                                f'<div class="answer-container">{response_text}</div>',
                                unsafe_allow_html=True
                            )
                            
                            update_progress(progress_placeholder, 100, "complete")
                            break
                            
                        elif event_type == 'error':
                            error_message = data.get('error', 'Une erreur inconnue s\'est produite')
                            response_placeholder.error(f"Erreur: {error_message}")
                            return None, None
                
                return response_text, sources
                
    except Exception as e:
        response_placeholder.error(f"Erreur de connexion: {str(e)}")
        return None, None

# Version synchrone pour appeler du code asynchrone dans Streamlit
def run_async_generation(retriever, query, n_results, include_sources, response_placeholder, progress_placeholder):
    """Exécute la génération asynchrone dans un contexte synchrone pour Streamlit"""
    # Choisir entre une implémentation locale ou via l'API
    use_api = False  # Mettre à True pour utiliser le serveur FastAPI, False pour génération locale
    
    if use_api:
        # Utiliser le serveur API
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                stream_from_api(query, n_results, include_sources, response_placeholder, progress_placeholder)
            )
        finally:
            loop.close()
    else:
        # Utiliser l'implémentation locale
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                generate_streaming_answer(retriever, query, n_results, include_sources, response_placeholder, progress_placeholder)
            )
        finally:
            loop.close()

# Fonction principale pour l'interface utilisateur
def main():
    """Fonction principale pour l'interface Streamlit"""
    
    # Initialiser les états de session si nécessaire
    if 'use_streaming' not in st.session_state:
        st.session_state.use_streaming = True
    
    # En-tête avec logo
    st.markdown('<div class="main-header">📊 OHAD\'AI Expert-Comptable</div>', unsafe_allow_html=True)
    
    # Barre latérale personnalisée
    with st.sidebar:
        st.image("https://www.ohada.org/wp-content/uploads/2022/03/Ohada-logo.jpg", width=150)
        st.markdown("### Navigation")
        
        st.markdown("- **Accueil**")
        st.markdown("- Recherche avancée")
        st.markdown("- Documentation OHADA")
        st.markdown("- À propos")
        
        st.markdown("### Paramètres")
        show_sources = st.checkbox("Afficher les sources", value=True)
        n_results = st.slider("Nombre de sources", min_value=3, max_value=10, value=5)
        
        # Option de streaming
        st.session_state.use_streaming = st.checkbox("Activer le streaming", value=st.session_state.use_streaming)
        
        st.markdown("---")
        st.markdown("© 2025 | OHAD'AI Expert-Comptable")
    
    # Zone de recherche principale
    st.markdown('<div class="search-card">', unsafe_allow_html=True)
    
    query = st.text_area("Posez votre question sur le plan comptable OHADA", 
                         placeholder="Exemple: Comment fonctionne l'amortissement dégressif dans le SYSCOHADA?",
                         height=100)
    
    col1, col2 = st.columns([1, 6])
    with col1:
        search_button = st.button("🔍 Rechercher", use_container_width=True)
    
    # Exemples de questions cliquables (à développer avec JavaScript dans une vraie application)
    st.markdown("<p>Suggestions :</p>", unsafe_allow_html=True)
    st.markdown("""
        <div>
            <span class="example-question">Comment fonctionne l'amortissement dégressif?</span>
            <span class="example-question">Structure du plan comptable OHADA</span>
            <span class="example-question">Comptabilisation des subventions</span>
            <span class="example-question">Traitement des écarts de conversion</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Initialiser le retriever
    retriever = create_ohada_query_api()
    
    # Traiter la requête lorsque le bouton est cliqué
    if retriever and search_button and query:
        if st.session_state.use_streaming:
            # Version streaming
            try:
                # Créer les espaces réservés pour la réponse et la progression
                response_placeholder = create_streaming_response_placeholder()
                progress_placeholder = st.empty()
                
                # Générer la réponse en streaming
                answer, sources = run_async_generation(
                    retriever, query, n_results, show_sources, 
                    response_placeholder, progress_placeholder
                )
                
                # Si la génération a réussi
                if answer and show_sources and sources:
                    # Afficher les sources
                    st.markdown("<h3>Sources utilisées</h3>", unsafe_allow_html=True)
                    
                    # Créer des cartes pour chaque source
                    for i, source in enumerate(sources):
                        # Formater les métadonnées
                        metadata = source["metadata"]
                        title = metadata.get("title", f"Document {i+1}")
                        partie_info = f"Partie {metadata['partie']}" if "partie" in metadata else ""
                        chapitre_info = f"Chapitre {metadata['chapitre']}" if "chapitre" in metadata else ""
                        
                        # Créer la carte de source style Perplexity
                        st.markdown(f"""
                        <div class="source-card">
                            <div class="source-title">{title}</div>
                            <div class="source-meta">
                                {partie_info} {chapitre_info} • Score de pertinence: {source['relevance_score']:.2f}
                            </div>
                            <div class="source-preview">{source['preview']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
            except Exception as e:
                st.error(f"Une erreur s'est produite lors de la génération en streaming : {str(e)}")
                st.info("Veuillez réessayer avec une autre question ou désactiver le streaming.")
        else:
            # Version classique sans streaming
            with st.spinner("Recherche en cours... Cela peut prendre quelques instants."):
                try:
                    # Exécuter la recherche
                    result = retriever.search_ohada_knowledge(
                        query=query,
                        n_results=n_results,
                        include_sources=show_sources
                    )
                    
                    # Afficher la réponse
                    st.markdown('<div class="answer-container">', unsafe_allow_html=True)
                    st.markdown(f"{result['answer']}")
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Afficher les sources si demandé
                    if show_sources and "sources" in result:
                        st.markdown("<h3>Sources utilisées</h3>", unsafe_allow_html=True)
                        
                        # Créer des cartes pour chaque source
                        for i, source in enumerate(result["sources"]):
                            # Formater les métadonnées
                            metadata = source["metadata"]
                            title = metadata.get("title", f"Document {i+1}")
                            partie_info = f"Partie {metadata['partie']}" if "partie" in metadata else ""
                            chapitre_info = f"Chapitre {metadata['chapitre']}" if "chapitre" in metadata else ""
                            
                            # Créer la carte de source style Perplexity
                            st.markdown(f"""
                            <div class="source-card">
                                <div class="source-title">{title}</div>
                                <div class="source-meta">
                                    {partie_info} {chapitre_info} • Score de pertinence: {source['relevance_score']:.2f}
                                </div>
                                <div class="source-preview">{source['preview']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Informations de performance
                    performance = result.get("performance", {})
                    total_time = performance.get("total_time_seconds", 0)
                    if total_time > 0:
                        st.markdown(f"<div style='text-align: right; color: var(--subtle-text); font-size: 0.8rem;'>Réponse générée en {format_time(total_time)}</div>", unsafe_allow_html=True)
                        
                except Exception as e:
                    st.error(f"Une erreur s'est produite lors de la recherche : {str(e)}")
                    st.info("Veuillez réessayer avec une autre question ou contacter l'administrateur si le problème persiste.")
    
    # Afficher un message d'accueil si aucune recherche n'a été effectuée
    elif not search_button:
        st.markdown("""
        <div class="answer-container" style="text-align: center;">
            <h2>Bienvenue sur OHAD'AI Expert-Comptable!</h2>
            <p>Assistant intelligent spécialisé sur le plan comptable OHADA</p>
            <p>Pour commencer, saisissez votre question dans le champ ci-dessus et cliquez sur "Rechercher".</p>
            <p><strong>Mode streaming activé</strong>: Visualisez la réponse au fur et à mesure qu'elle est générée!</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()