import requests
import pandas as pd
from collections import Counter
import concurrent.futures
import time
import yake
from textrazor import TextRazor
import trafilatura
from .text_analysis import extract_keywords, analyze_text_with_textrazor

def get_serp_results(keyword, location, api_key):
    """Récupère les résultats SERP via ValueSERP API."""
    if not api_key:
        raise ValueError("Clé API ValueSERP manquante")
        
    params = {
        'api_key': api_key,
        'q': keyword,
        'location': location,
        'google_domain': 'google.fr',
        'gl': 'fr',
        'hl': 'fr',
        'num': 30
    }
    
    try:
        response = requests.get('https://api.valueserp.com/search', params=params)
        response.raise_for_status()
        data = response.json()
        
        if 'organic_results' not in data:
            raise ValueError("Pas de résultats organiques dans la réponse")
            
        return [result['link'] for result in data['organic_results']]
    except Exception as e:
        print(f"Erreur lors de la récupération SERP: {str(e)}")
        return None

def extract_text_from_url(url):
    """Extrait le texte d'une URL en utilisant trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            return text if text else None
    except Exception as e:
        print(f"Erreur lors de l'extraction du texte de {url}: {str(e)}")
    return None

def analyze_url_content(url, textrazor_api_key, language="fr"):
    """Analyse le contenu d'une URL avec YAKE et TextRazor."""
    text = extract_text_from_url(url)
    if not text:
        return None
        
    try:
        # Analyse YAKE
        keywords_df = extract_keywords(text, language=language)
        
        # Analyse TextRazor
        _, topics, entities_df = analyze_text_with_textrazor(text, textrazor_api_key)
        
        return {
            'url': url,
            'text': text,
            'keywords': keywords_df.to_dict('records') if not keywords_df.empty else [],
            'topics': topics if topics else [],
            'entities': entities_df.to_dict('records') if not entities_df.empty else []
        }
    except Exception as e:
        print(f"Erreur lors de l'analyse de {url}: {str(e)}")
        return None

def analyze_serp_results(keyword, location, valueserp_api_key, textrazor_api_key, user_url=None, language="fr"):
    """Analyse complète des résultats SERP avec comparaison."""
    try:
        # Récupérer les URLs des SERP
        urls = get_serp_results(keyword, location, valueserp_api_key)
        if not urls:
            return None
            
        # Limiter à 10 URLs pour l'analyse
        urls = urls[:10]
        
        # Analyser chaque URL
        analyzed_results = []
        all_keywords = []
        all_topics = []
        all_entities = []
        
        for url in urls:
            result = analyze_url_content(url, textrazor_api_key, language)
            if result:
                analyzed_results.append(result)
                all_keywords.extend(result['keywords'])
                all_topics.extend(result['topics'])
                all_entities.extend(result['entities'])
        
        # Analyser l'URL de l'utilisateur si fournie
        user_data = None
        if user_url:
            user_data = analyze_url_content(user_url, textrazor_api_key, language)
        
        # Agréger les résultats
        keywords_data = []
        for kw in all_keywords:
            keywords_data.append({
                'keyword': kw['keyword'],
                'avg_score': kw['score'],
                'total_occurrences': kw['occurrences'],
                'urls_count': sum(1 for r in analyzed_results if any(k['keyword'] == kw['keyword'] for k in r['keywords']))
            })
        
        # Créer les DataFrames
        keywords_df = pd.DataFrame(keywords_data).groupby('keyword').agg({
            'avg_score': 'mean',
            'total_occurrences': 'sum',
            'urls_count': 'max'
        }).reset_index()
        
        topics_data = []
        for topic in set(all_topics):
            count = sum(1 for r in analyzed_results if topic in r['topics'])
            topics_data.append({
                'topic': topic,
                'count': count,
                'avg_score': count / len(analyzed_results)
            })
        
        topics_df = pd.DataFrame(topics_data)
        
        entities_data = []
        for entity in all_entities:
            entities_data.append({
                'entity': entity['entity'],
                'total_count': entity['count'],
                'avg_relevance': entity['relevance']
            })
        
        entities_df = pd.DataFrame(entities_data).groupby('entity').agg({
            'total_count': 'sum',
            'avg_relevance': 'mean'
        }).reset_index()
        
        result = {
            'query': keyword,
            'location': location,
            'urls': urls,
            'keywords': keywords_df.to_dict('records'),
            'topics': topics_df.to_dict('records'),
            'entities': entities_df.to_dict('records'),
            'analyzed_results': analyzed_results
        }
        
        # Ajouter la comparaison si une URL utilisateur est fournie
        if user_data:
            result['comparison'] = compare_with_serp(user_data, {
                'keywords': result['keywords'],
                'topics': result['topics'],
                'entities': result['entities']
            })
        
        return result
        
    except Exception as e:
        print(f"Erreur lors de l'analyse SERP: {str(e)}")
        return None

def compare_with_serp(user_data, serp_data):
    """Compare les données de l'URL utilisateur avec les données SERP."""
    if not user_data or not serp_data:
        return None
        
    comparison = {
        'missing_keywords': [],
        'keyword_gaps': [],
        'missing_topics': [],
        'topic_coverage': 0,
        'entity_coverage': 0,
        'recommendations': []
    }
    
    # Analyse des mots-clés manquants
    serp_keywords = {k['keyword']: k for k in serp_data['keywords']}
    user_keywords = {k['keyword']: k for k in user_data['keywords']}
    
    for kw, data in serp_keywords.items():
        if kw not in user_keywords and data['urls_count'] >= 3:
            comparison['missing_keywords'].append({
                'keyword': kw,
                'importance': data['urls_count'],
                'serp_occurrences': data['total_occurrences']
            })
    
    # Analyse des topics manquants
    serp_topics = set(t['topic'] for t in serp_data['topics'])
    user_topics = set(user_data['topics'])
    
    comparison['missing_topics'] = [
        {'topic': topic} for topic in serp_topics - user_topics
    ]
    
    # Calculer les couvertures
    if serp_topics:
        comparison['topic_coverage'] = (len(user_topics) / len(serp_topics)) * 100
    
    # Générer des recommandations
    if comparison['missing_keywords']:
        comparison['recommendations'].append({
            'priority': 'high',
            'message': f"Ajouter les mots-clés manquants importants : {', '.join([k['keyword'] for k in comparison['missing_keywords'][:5]])}"
        })
    
    if comparison['missing_topics']:
        comparison['recommendations'].append({
            'priority': 'medium',
            'message': f"Couvrir les thématiques manquantes : {', '.join([t['topic'] for t in comparison['missing_topics'][:3]])}"
        })
    
    return comparison