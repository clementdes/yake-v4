# ... (le code existant reste le même jusqu'à la section "Analyse comparative avec l'URL de l'utilisateur")

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

# ... (le reste du code reste identique)