import requests
import pandas as pd
from collections import Counter
import concurrent.futures
import time
import yake
from textrazor import TextRazor
from bs4 import BeautifulSoup
import trafilatura

def extract_text_from_url(url):
    """Extrait le texte d'une URL en utilisant trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False, 
                                     include_tables=False, no_fallback=True)
            if text:
                return text.strip()
    except Exception as e:
        print(f"Erreur lors de l'extraction du texte de {url}: {str(e)}")
    return None

def analyze_url_with_yake(text, language="fr", max_keywords=20):
    """Analyse le texte avec YAKE."""
    try:
        kw_extractor = yake.KeywordExtractor(
            lan=language,
            n=3,
            dedupLim=0.9,
            top=max_keywords,
            features=None
        )
        keywords = kw_extractor.extract_keywords(text)
        return [{'keyword': kw, 'score': score, 'occurrences': text.lower().count(kw.lower())} 
                for kw, score in keywords]
    except Exception as e:
        print(f"Erreur YAKE: {str(e)}")
        return []

def analyze_url_with_textrazor(url, text, api_key):
    """Analyse le texte avec TextRazor."""
    if not api_key:
        return None, None
    
    try:
        client = TextRazor(api_key, extractors=["entities", "topics", "words"])
        client.set_cleanup_mode("cleanHTML")
        response = client.analyze(text)
        
        # Extraction des topics
        topics = [{'topic': topic.label, 'score': topic.score} 
                 for topic in response.topics()]
        
        # Extraction des entités avec métadonnées
        entities = []
        entity_counts = Counter()
        
        for entity in response.entities():
            entity_counts[entity.id] += 1
            if len(entities) == 0 or entity.id not in [e['entity'] for e in entities]:
                entities.append({
                    'entity': entity.id,
                    'type': entity.freebase_types[0] if entity.freebase_types else 'Unknown',
                    'relevance': entity.relevance_score,
                    'confidence': entity.confidence_score,
                    'wikipedia_link': entity.wikipedia_link,
                    'count': 1
                })
        
        # Mise à jour des compteurs
        for entity in entities:
            entity['count'] = entity_counts[entity['entity']]
        
        return topics, entities
        
    except Exception as e:
        print(f"Erreur TextRazor: {str(e)}")
        return None, None

def analyze_url_content(url, textrazor_api_key, language="fr"):
    """Analyse complète du contenu d'une URL."""
    try:
        # Extraction du texte
        text = extract_text_from_url(url)
        if not text:
            return None
            
        # Analyse YAKE
        keywords = analyze_url_with_yake(text, language)
        
        # Analyse TextRazor
        topics, entities = analyze_url_with_textrazor(url, text, textrazor_api_key)
        
        return {
            'url': url,
            'text': text[:1000],  # Limiter la taille du texte stocké
            'text_length': len(text),
            'keywords': keywords,
            'topics': topics if topics else [],
            'entities': entities if entities else [],
            'analysis_timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        print(f"Erreur lors de l'analyse de {url}: {str(e)}")
        return None

def analyze_serp_results(keyword, location, valueserp_api_key, textrazor_api_key, user_url=None, language="fr"):
    """Analyse complète des résultats SERP."""
    if not valueserp_api_key or not textrazor_api_key:
        return None
    
    try:
        # Récupération des résultats SERP
        params = {
            "api_key": valueserp_api_key,
            "q": keyword,
            "location": location,
            "num": 30,
            "output": "json"
        }
        
        response = requests.get("https://api.valueserp.com/search", params=params)
        response.raise_for_status()
        results = response.json()
        
        if 'organic_results' not in results:
            return None
            
        urls = [result['link'] for result in results['organic_results']]
        
        # Analyse parallèle des 10 premiers résultats
        analyzed_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {
                executor.submit(analyze_url_content, url, textrazor_api_key, language): url 
                for url in urls[:10]
            }
            
            for future in concurrent.futures.as_completed(future_to_url):
                result = future.result()
                if result:
                    analyzed_results.append(result)
                time.sleep(1)  # Respect des limites d'API
        
        # Analyse de l'URL de l'utilisateur
        user_data = None
        if user_url:
            user_data = analyze_url_content(user_url, textrazor_api_key, language)
        
        # Agrégation des résultats
        all_keywords = []
        all_topics = []
        all_entities = []
        
        for result in analyzed_results:
            all_keywords.extend(result['keywords'])
            all_topics.extend(result['topics'])
            all_entities.extend(result['entities'])
        
        # Analyse statistique des mots-clés
        keyword_stats = {}
        for kw in all_keywords:
            keyword = kw['keyword']
            if keyword not in keyword_stats:
                keyword_stats[keyword] = {
                    'keyword': keyword,
                    'total_occurrences': 0,
                    'score': kw['score'],
                    'urls_count': 0,
                    'avg_score': 0
                }
            keyword_stats[keyword]['total_occurrences'] += kw['occurrences']
            keyword_stats[keyword]['urls_count'] += 1
            keyword_stats[keyword]['avg_score'] = (keyword_stats[keyword]['avg_score'] * 
                (keyword_stats[keyword]['urls_count'] - 1) + kw['score']) / keyword_stats[keyword]['urls_count']
        
        # Création des DataFrames
        keywords_df = pd.DataFrame(list(keyword_stats.values()))
        if not keywords_df.empty:
            keywords_df['average_occurrences'] = keywords_df['total_occurrences'] / keywords_df['urls_count']
            keywords_df = keywords_df.sort_values('total_occurrences', ascending=False)
        
        # Analyse statistique des topics
        topic_stats = {}
        for topic in all_topics:
            topic_name = topic['topic']
            if topic_name not in topic_stats:
                topic_stats[topic_name] = {
                    'topic': topic_name,
                    'count': 0,
                    'avg_score': 0,
                    'urls_count': 0
                }
            topic_stats[topic_name]['count'] += 1
            topic_stats[topic_name]['urls_count'] += 1
            topic_stats[topic_name]['avg_score'] = (topic_stats[topic_name]['avg_score'] * 
                (topic_stats[topic_name]['urls_count'] - 1) + topic['score']) / topic_stats[topic_name]['urls_count']
        
        topics_df = pd.DataFrame(list(topic_stats.values()))
        if not topics_df.empty:
            topics_df = topics_df.sort_values('count', ascending=False)
        
        # Analyse statistique des entités
        entity_stats = {}
        for entity in all_entities:
            entity_name = entity['entity']
            if entity_name not in entity_stats:
                entity_stats[entity_name] = {
                    'entity': entity_name,
                    'type': entity['type'],
                    'total_count': 0,
                    'urls_count': 0,
                    'avg_relevance': 0,
                    'avg_confidence': 0,
                    'wikipedia_link': entity.get('wikipedia_link', '')
                }
            entity_stats[entity_name]['total_count'] += entity['count']
            entity_stats[entity_name]['urls_count'] += 1
            entity_stats[entity_name]['avg_relevance'] = (entity_stats[entity_name]['avg_relevance'] * 
                (entity_stats[entity_name]['urls_count'] - 1) + entity['relevance']) / entity_stats[entity_name]['urls_count']
            entity_stats[entity_name]['avg_confidence'] = (entity_stats[entity_name]['avg_confidence'] * 
                (entity_stats[entity_name]['urls_count'] - 1) + entity['confidence']) / entity_stats[entity_name]['urls_count']
        
        entities_df = pd.DataFrame(list(entity_stats.values()))
        if not entities_df.empty:
            entities_df = entities_df.sort_values('total_count', ascending=False)
        
        return {
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
        
    except Exception as e:
        print(f"Erreur SERP: {str(e)}")
        return None