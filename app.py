import streamlit as st
import nltk
from nltk.corpus import stopwords
import pandas as pd
import os
import textrazor
import requests
from collections import Counter
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime
import json
from utils.text_analysis import extract_keywords, analyze_text_with_textrazor
from utils.serp_analysis import analyze_serp_results, compare_with_serp
from utils.visualization import create_keywords_chart, generate_wordcloud

# Configuration de la page
st.set_page_config(
    page_title="SEO Content Analyzer Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styles CSS personnalisés
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        margin-top: 1rem;
    }
    .reportTitle {
        color: #1f77b4;
        text-align: center;
        padding: 1rem;
    }
    .metric-card {
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: #f8f9fa;
        border-radius: 0.3rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialisation de NLTK
nltk_data_dir = os.path.join(os.path.expanduser('~'), 'nltk_data')
if not os.path.exists(nltk_data_dir):
    os.makedirs(nltk_data_dir)
nltk.data.path.append(nltk_data_dir)
try:
    nltk.download('stopwords', download_dir=nltk_data_dir)
    nltk.download('punkt', download_dir=nltk_data_dir)
except Exception as e:
    st.error(f"Erreur lors du téléchargement des ressources NLTK : {e}")

# Fonction pour sauvegarder l'historique
def save_analysis_history(data, analysis_type):
    if 'analysis_history' not in st.session_state:
        st.session_state.analysis_history = []
    
    history_entry = {
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'type': analysis_type,
        'data': data
    }
    st.session_state.analysis_history.append(history_entry)

# Navigation principale
st.sidebar.title("SEO Content Analyzer Pro")
page = st.sidebar.radio("Navigation", [
    "Analyse de Texte",
    "Analyse d'URL",
    "Recherche SERP",
    "Historique des Analyses",
    "Configuration"
])

# Configuration globale dans la sidebar
with st.sidebar.expander("Configuration Globale"):
    max_keywords = st.number_input("Nombre max de mots-clés", 10, 200, 100)
    min_char_length = st.number_input("Longueur min des mots-clés", 3, 10, 3)
    language = st.selectbox("Langue", ["fr", "en", "es", "de", "it"])

# Clés API dans la sidebar
textrazor_api_key = st.sidebar.text_input("Clé API TextRazor", type="password")
valueserp_api_key = st.sidebar.text_input("Clé API ValueSERP", type="password")

# Page principale
if page == "Analyse de Texte":
    st.title("Analyse de Texte Avancée")
    
    text_input = st.text_area("Entrez votre texte ici:", height=200)
    
    if st.button("Analyser le texte"):
        if text_input.strip():
            # Analyse YAKE
            keywords_df = extract_keywords(text_input, language=language, max_keywords=max_keywords)
            
            # Analyse TextRazor
            _, topics, entities_df = analyze_text_with_textrazor(text_input, textrazor_api_key)
            
            # Affichage des résultats
            st.subheader("Résultats de l'analyse")
            
            # Mots-clés
            st.subheader("Mots-clés extraits")
            st.dataframe(keywords_df)
            
            # Visualisations
            col1, col2 = st.columns(2)
            
            with col1:
                st.plotly_chart(create_keywords_chart(keywords_df))
            
            with col2:
                wordcloud_image = generate_wordcloud(text_input)
                st.image(wordcloud_image)
            
            # Topics et Entités
            if topics:
                st.subheader("Topics identifiés")
                st.write(", ".join(topics))
            
            if not entities_df.empty:
                st.subheader("Entités extraites")
                st.dataframe(entities_df)
            
            # Sauvegarde dans l'historique
            save_analysis_history({
                'text': text_input[:200] + '...',
                'keywords': keywords_df.to_dict('records'),
                'topics': topics,
                'entities': entities_df.to_dict('records') if not entities_df.empty else []
            }, 'text_analysis')

elif page == "Analyse d'URL":
    st.title("Analyse de contenu via URL")
    
    url_input = st.text_input("Entrez l'URL ici:")
    
    if st.button("Analyser l'URL"):
        if url_input.strip():
            # Analyse TextRazor de l'URL
            text, topics, entities_df = analyze_text_with_textrazor(url_input, textrazor_api_key, is_url=True)
            
            if text:
                # Analyse YAKE du texte extrait
                keywords_df = extract_keywords(text, language=language, max_keywords=max_keywords)
                
                # Affichage des résultats
                st.subheader("Texte extrait")
                st.write(text[:500] + "...")
                
                # Mots-clés
                st.subheader("Mots-clés extraits")
                st.dataframe(keywords_df)
                
                # Visualisations
                col1, col2 = st.columns(2)
                
                with col1:
                    st.plotly_chart(create_keywords_chart(keywords_df))
                
                with col2:
                    wordcloud_image = generate_wordcloud(text)
                    st.image(wordcloud_image)
                
                # Topics et Entités
                if topics:
                    st.subheader("Topics identifiés")
                    st.write(", ".join(topics))
                
                if not entities_df.empty:
                    st.subheader("Entités extraites")
                    st.dataframe(entities_df)
                
                # Sauvegarde dans l'historique
                save_analysis_history({
                    'url': url_input,
                    'text': text[:200] + '...',
                    'keywords': keywords_df.to_dict('records'),
                    'topics': topics,
                    'entities': entities_df.to_dict('records') if not entities_df.empty else []
                }, 'url_analysis')

elif page == "Recherche SERP":
    st.title("Analyse des SERP")
    
    keyword_input = st.text_input("Entrez un mot-clé pour la recherche:")
    location_query = st.text_input("Entrez une localisation pour les SERP:")
    user_url = st.text_input("Votre URL (optionnel):")
    
    if st.button("Analyser les SERP"):
        if keyword_input and location_query:
            results = analyze_serp_results(
                keyword_input,
                location_query,
                valueserp_api_key,
                textrazor_api_key,
                user_url,
                language
            )
            
            if results:
                st.subheader("Résultats de l'analyse SERP")
                
                # URLs analysées
                st.subheader("URLs analysées")
                for idx, url in enumerate(results['urls'], 1):
                    st.write(f"{idx}. {url}")
                
                # Mots-clés globaux
                if results['keywords']:
                    st.subheader("Analyse globale des mots-clés")
                    keywords_df = pd.DataFrame(results['keywords'])
                    st.dataframe(keywords_df)
                    
                    # Visualisation des mots-clés
                    st.plotly_chart(create_keywords_chart(keywords_df))
                
                # Topics globaux
                if results['topics']:
                    st.subheader("Topics principaux")
                    topics_df = pd.DataFrame(results['topics'])
                    st.dataframe(topics_df)
                
                # Entités globales
                if results['entities']:
                    st.subheader("Entités principales")
                    entities_df = pd.DataFrame(results['entities'])
                    st.dataframe(entities_df)
                
                # Analyse comparative avec l'URL de l'utilisateur
                if results.get('comparison'):
                    st.subheader("Analyse comparative de votre URL")
                    comparison = results['comparison']
                    
                    # Métriques de couverture
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Couverture des topics", f"{comparison['topic_coverage']:.1f}%")
                    with col2:
                        st.metric("Couverture des entités", f"{comparison['entity_coverage']:.1f}%")
                    
                    # Mots-clés manquants
                    if comparison['missing_keywords']:
                        st.subheader("Mots-clés manquants importants")
                        missing_kw_df = pd.DataFrame(comparison['missing_keywords'])
                        st.dataframe(missing_kw_df)
                    
                    # Écarts de fréquence
                    if comparison['keyword_gaps']:
                        st.subheader("Mots-clés sous-utilisés")
                        gaps_df = pd.DataFrame(comparison['keyword_gaps'])
                        st.dataframe(gaps_df)
                    
                    # Topics manquants
                    if comparison['missing_topics']:
                        st.subheader("Topics manquants")
                        missing_topics_df = pd.DataFrame(comparison['missing_topics'])
                        st.dataframe(missing_topics_df)
                    
                    # Recommandations
                    if comparison['recommendations']:
                        st.subheader("Recommandations d'optimisation")
                        for rec in comparison['recommendations']:
                            priority_color = {
                                'high': 'red',
                                'medium': 'orange',
                                'low': 'blue'
                            }.get(rec['priority'], 'gray')
                            
                            st.markdown(f"""
                            <div class="metric-card" style="border-left: 4px solid {priority_color}">
                                <strong>Priorité {rec['priority']}</strong><br>
                                {rec['message']}
                            </div>
                            """, unsafe_allow_html=True)
                
                # Sauvegarde dans l'historique
                save_analysis_history({
                    'keyword': keyword_input,
                    'location': location_query,
                    'user_url': user_url,
                    'results': results
                }, 'serp_analysis')

elif page == "Historique des Analyses":
    st.title("Historique des Analyses")
    
    if 'analysis_history' in st.session_state and st.session_state.analysis_history:
        for entry in reversed(st.session_state.analysis_history):
            with st.expander(f"{entry['type']} - {entry['date']}"):
                st.json(entry['data'])
    else:
        st.info("Aucun historique d'analyse disponible.")

elif page == "Configuration":
    st.title("Configuration")
    
    st.subheader("Paramètres d'analyse")
    st.write("Configurez les paramètres globaux d'analyse dans la barre latérale.")
    
    st.subheader("Clés API")
    st.write("""
    Pour utiliser toutes les fonctionnalités de l'application, vous devez configurer les clés API suivantes :
    - TextRazor : Pour l'analyse sémantique et l'extraction d'entités
    - ValueSERP : Pour l'analyse des résultats de recherche Google
    """)
    
    st.subheader("À propos")
    st.write("""
    SEO Content Analyzer Pro est un outil d'analyse de contenu qui combine plusieurs technologies :
    - YAKE pour l'extraction de mots-clés
    - TextRazor pour l'analyse sémantique
    - ValueSERP pour l'analyse des SERP
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("© 2024 SEO Content Analyzer Pro")
