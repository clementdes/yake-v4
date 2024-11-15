import streamlit as st
import pandas as pd
from datetime import datetime
import os
import nltk
from utils.text_analysis import extract_keywords, analyze_text_with_textrazor
from utils.serp_analysis import analyze_serp_results
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
    .main { padding: 2rem; }
    .stButton>button { width: 100%; margin-top: 1rem; }
    .reportTitle { color: #1f77b4; text-align: center; padding: 1rem; }
    .stAlert { padding: 1rem; margin-bottom: 1rem; border-radius: 0.5rem; }
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

# Configuration globale
with st.sidebar.expander("Configuration Globale"):
    max_keywords = st.number_input("Nombre max de mots-clés", 10, 200, 100)
    min_char_length = st.number_input("Longueur min des mots-clés", 3, 10, 3)
    language = st.selectbox("Langue", ["fr", "en", "es", "de", "it"])

# Pages
if page == "Analyse de Texte":
    st.title("Analyse de Texte Avancée")
    
    text_input = st.text_area("Entrez votre texte ici:", height=200)
    
    if st.button("Analyser le texte"):
        if text_input.strip():
            keywords_df = extract_keywords(text_input, language, max_keywords)
            
            st.subheader("Résultats de l'analyse")
            st.dataframe(keywords_df)
            
            chart = create_keywords_chart(keywords_df)
            if chart:
                st.plotly_chart(chart)
            
            wordcloud_image = generate_wordcloud(text_input)
            st.image(wordcloud_image)
            
            save_analysis_history({
                'text': text_input[:200] + '...',
                'keywords': keywords_df.to_dict('records')
            }, 'text_analysis')

elif page == "Analyse d'URL":
    st.title("Analyse d'URL")
    textrazor_api_key = st.text_input("Clé API TextRazor", type="password")
    url_input = st.text_input("Entrez l'URL à analyser:")
    
    if st.button("Analyser l'URL"):
        if url_input and textrazor_api_key:
            text, topics, entities_df = analyze_text_with_textrazor(url_input, textrazor_api_key, is_url=True)
            if text:
                st.subheader("Contenu extrait")
                st.write(text[:500] + "...")
                
                if topics:
                    st.subheader("Topics identifiés")
                    st.write(", ".join(topics))
                
                if not entities_df.empty:
                    st.subheader("Entités identifiées")
                    st.dataframe(entities_df)
                
                save_analysis_history({
                    'url': url_input,
                    'topics': topics,
                    'entities': entities_df.to_dict('records')
                }, 'url_analysis')

elif page == "Recherche SERP":
    st.title("Analyse SERP")
    
    col1, col2 = st.columns(2)
    with col1:
        valueserp_api_key = st.text_input("Clé API ValueSERP", type="password")
        textrazor_api_key = st.text_input("Clé API TextRazor", type="password")
    
    with col2:
        keyword = st.text_input("Mot-clé à analyser:")
        location = st.text_input("Localisation (ex: France):")
        user_url = st.text_input("Votre URL (optionnel):")
    
    if st.button("Analyser les SERP"):
        if keyword and location and valueserp_api_key and textrazor_api_key:
            with st.spinner("Analyse en cours..."):
                results = analyze_serp_results(keyword, location, valueserp_api_key, textrazor_api_key, user_url)
                
                if results:
                    st.subheader("URLs analysées")
                    st.write(results['urls'])
                    
                    if results['keywords']:
                        st.subheader("Mots-clés principaux")
                        keywords_df = pd.DataFrame(results['keywords'])
                        st.dataframe(keywords_df)
                        
                        chart = create_keywords_chart(keywords_df)
                        if chart:
                            st.plotly_chart(chart)
                    
                    if results['topics']:
                        st.subheader("Topics principaux")
                        topics_counter = Counter(results['topics'])
                        topics_df = pd.DataFrame(topics_counter.most_common(), columns=['Topic', 'Occurrences'])
                        st.dataframe(topics_df)
                    
                    if results['user_data']:
                        st.subheader("Analyse de votre URL")
                        st.write("Comparaison avec les concurrents")
                        user_keywords_df = pd.DataFrame(results['user_data']['keywords'])
                        st.dataframe(user_keywords_df)
                    
                    save_analysis_history({
                        'keyword': keyword,
                        'location': location,
                        'results': results
                    }, 'serp_analysis')

elif page == "Historique des Analyses":
    st.title("Historique des Analyses")
    
    if 'analysis_history' in st.session_state and st.session_state.analysis_history:
        for entry in st.session_state.analysis_history:
            with st.expander(f"{entry['type']} - {entry['date']}"):
                st.json(entry['data'])
    else:
        st.info("Aucun historique d'analyse disponible.")

elif page == "Configuration":
    st.title("Configuration")
    
    st.subheader("APIs")
    valueserp_api_key = st.text_input("Clé API ValueSERP par défaut", type="password")
    textrazor_api_key = st.text_input("Clé API TextRazor par défaut", type="password")
    
    if st.button("Sauvegarder la configuration"):
        st.session_state.valueserp_api_key = valueserp_api_key
        st.session_state.textrazor_api_key = textrazor_api_key
        st.success("Configuration sauvegardée avec succès!")

if __name__ == "__main__":
    st.sidebar.markdown("---")
    st.sidebar.markdown("© 2024 SEO Content Analyzer Pro")