import plotly.graph_objects as go
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import pandas as pd

def create_keywords_chart(keywords_data, top_n=20):
    """Crée un graphique des mots-clés les plus fréquents."""
    if isinstance(keywords_data, list):
        df = pd.DataFrame(keywords_data)
    else:
        df = keywords_data.copy()
    
    # Adapter les noms de colonnes selon la source des données
    if 'total_occurrences' in df.columns:
        df = df.rename(columns={'total_occurrences': 'occurrences', 'keyword': 'keyword'})
    elif 'Nombre d\'occurrences total' in df.columns:
        df = df.rename(columns={'Nombre d\'occurrences total': 'occurrences', 'Mot Yake': 'keyword'})
    
    # Vérifier que les colonnes nécessaires existent
    required_columns = {'keyword', 'occurrences'}
    if not all(col in df.columns for col in required_columns):
        print("Colonnes manquantes:", required_columns - set(df.columns))
        # Créer un graphique vide plutôt que de retourner None
        fig = go.Figure()
        fig.update_layout(
            title='Données insuffisantes pour générer le graphique',
            annotations=[{
                'text': 'Données manquantes',
                'xref': 'paper',
                'yref': 'paper',
                'showarrow': False,
                'font': {'size': 20}
            }]
        )
        return fig
    
    # Trier et sélectionner les top_n mots-clés
    df_sorted = df.sort_values('occurrences', ascending=True).tail(top_n)
    
    fig = go.Figure(go.Bar(
        x=df_sorted['occurrences'],
        y=df_sorted['keyword'],
        orientation='h'
    ))
    
    fig.update_layout(
        title=f'Top {top_n} mots-clés par nombre d\'occurrences',
        xaxis_title='Nombre d\'occurrences',
        yaxis_title='Mots-clés',
        height=600,
        showlegend=False
    )
    
    return fig

def generate_wordcloud(text):
    """Génère un nuage de mots à partir d'un texte."""
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return buf