import requests
import pandas as pd
from collections import Counter
import concurrent.futures
import time
import yake
from textrazor import TextRazor
import trafilatura

def compare_with_serp(user_data, serp_data):
    """Compare les données de l'URL utilisateur avec les données SERP."""
    if not user_data or not serp_data:
        return None
        
    comparison = {
        'missing_keywords': [],
        'keyword_gaps': [],
        'missing_topics': [],
        'topic_coverage': 0,
        'missing_entities': [],
        'entity_coverage': 0,
        'recommendations': []
    }
    
    # Analyse des mots-clés manquants
    serp_keywords = {k['keyword']: k for k in serp_data['keywords']}
    user_keywords = {k['keyword']: k for k in user_data['keywords']} if user_data['keywords'] else {}
    
    # Identifier les mots-clés manquants importants
    for kw, data in serp_keywords.items():
        if kw not in user_keywords:
            # Calculer l'importance du mot-clé manquant
            importance_score = (data['urls_count'] / 10) * (1 / (data['avg_score'] + 0.1))
            if importance_score > 0.3:  # Seuil d'importance
                comparison['missing_keywords'].append({
                    'keyword': kw,
                    'importance_score': importance_score,
                    'serp_occurrences': data['total_occurrences'],
                    'urls_count': data['urls_count'],
                    'avg_score': data['avg_score']
                })
    
    # Trier les mots-clés manquants par importance
    comparison['missing_keywords'].sort(key=lambda x: x['importance_score'], reverse=True)
    
    # Analyse des écarts de fréquence pour les mots-clés présents
    for kw, user_data in user_keywords.items():
        if kw in serp_keywords:
            serp_avg = serp_keywords[kw]['average_occurrences']
            user_count = user_data['occurrences']
            if user_count < serp_avg * 0.5:  # Si moins de 50% de la moyenne
                comparison['keyword_gaps'].append({
                    'keyword': kw,
                    'user_count': user_count,
                    'serp_average': serp_avg,
                    'difference_percentage': ((serp_avg - user_count) / serp_avg) * 100
                })
    
    # Trier les écarts par différence de pourcentage
    comparison['keyword_gaps'].sort(key=lambda x: x['difference_percentage'], reverse=True)
    
    # Analyse des topics manquants
    serp_topics = {t['topic']: t for t in serp_data['topics']}
    user_topics = {t['topic']: t for t in user_data['topics']} if user_data['topics'] else {}
    
    for topic, data in serp_topics.items():
        if topic not in user_topics and data['count'] > 1:  # Topics présents dans plus d'une URL
            comparison['missing_topics'].append({
                'topic': topic,
                'serp_count': data['count'],
                'avg_score': data['avg_score']
            })
    
    # Calculer la couverture des topics
    if serp_topics:
        comparison['topic_coverage'] = (len(user_topics) / len(serp_topics)) * 100
    
    # Analyse des entités manquantes
    serp_entities = {e['entity']: e for e in serp_data['entities']}
    user_entities = {e['entity']: e for e in user_data['entities']} if user_data['entities'] else {}
    
    for entity, data in serp_entities.items():
        if entity not in user_entities and data['total_count'] > 2:  # Entités fréquentes
            comparison['missing_entities'].append({
                'entity': entity,
                'type': data['type'],
                'serp_count': data['total_count'],
                'avg_relevance': data['avg_relevance']
            })
    
    # Calculer la couverture des entités
    if serp_entities:
        comparison['entity_coverage'] = (len(user_entities) / len(serp_entities)) * 100
    
    # Générer des recommandations
    if comparison['missing_keywords']:
        comparison['recommendations'].append({
            'type': 'keywords',
            'priority': 'high',
            'message': f"Ajouter les mots-clés manquants importants : {', '.join([k['keyword'] for k in comparison['missing_keywords'][:5]])}"
        })
    
    if comparison['keyword_gaps']:
        comparison['recommendations'].append({
            'type': 'frequency',
            'priority': 'medium',
            'message': f"Augmenter la fréquence des mots-clés sous-utilisés : {', '.join([k['keyword'] for k in comparison['keyword_gaps'][:5]])}"
        })
    
    if comparison['topic_coverage'] < 70:
        comparison['recommendations'].append({
            'type': 'topics',
            'priority': 'medium',
            'message': f"Améliorer la couverture thématique en ajoutant les topics manquants : {', '.join([t['topic'] for t in comparison['missing_topics'][:3]])}"
        })
    
    return comparison

# Le reste du code reste identique jusqu'à la fonction analyze_serp_results où nous ajoutons la comparaison

def analyze_serp_results(keyword, location, valueserp_api_key, textrazor_api_key, user_url=None, language="fr"):
    """Analyse complète des résultats SERP avec comparaison."""
    # Le code existant reste le même jusqu'à la fin
    
    try:
        # ... (code existant)
        
        result = {
            'query': keyword,
            'location': location,
            'urls': urls,
            'keywords': keywords_df.to_dict('records') if not keywords_df.empty else [],
            'topics': topics_df.to_dict('records') if not topics_df.empty else [],
            'entities': entities_df.to_dict('records') if not entities_df.empty else [],
            'analyzed_results': analyzed_results,
            'user_data': user_data,
            'analysis_timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
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
        print(f"Erreur SERP: {str(e)}")
        return None