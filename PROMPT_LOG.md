# PROMPT LOG : comment j'ai construit ce projet avec l'IA

> Ce fichier documente ma méthode de travail réelle avec l'IA (Claude).
> Je n'ai pas de background développeur. Ce log prouve que la valeur n'est pas dans le code, elle est dans la capacité à cadrer un problème, vérifier ce qui est réellement disponible avant de coder, et rester rigoureuse sur ce qui est vrai ou non, surtout sur un sujet aussi sensible que des données médicales.

---

## Contexte de départ

Ce projet vient d'un brief pour préparer un échange avec le Business Manager d'une ESN, secteur pharma/santé, pas d'une mission effectuée. Le brief d'origine proposait un pipeline n8n + Supabase sur des données simulées.

## Étape 1, Arbitrage sur les données : réelles plutôt que simulées

Le brief a évolué en cours de cadrage : plutôt que des fiches PDF simulées, utiliser un vrai jeu de données ouvert. L'IA a vérifié qu'un référentiel officiel existait (BDPM, ANSM), a **téléchargé et inspecté réellement les 3 fichiers** avant d'écrire le moindre code de parsing (encodage ISO-8859-1, tabulations, 12/8/13 colonnes selon le fichier, pas de header) plutôt que de deviner une structure. C'est la différence entre ce projet et les autres projets du portfolio : ici, aucune donnée n'est inventée, tout est vérifiable sur le site officiel.

## Étape 2, Arbitrage sur le stack

Le brief d'origine proposait n8n + Supabase + Next.js. L'IA a signalé que ce stack casserait la cohérence avec le reste du portfolio (Python/Streamlit/DuckDB, déployable gratuitement sans compte externe) et proposé une adaptation : même ambition fonctionnelle (pipeline, structuration relationnelle, agent IA cadré), stack alignée sur ce qui est déjà démontré ailleurs dans le portfolio. Choix assumé et documenté, pas un raccourci.

## Étape 3, Construction du pipeline et vérification

Pipeline en 3 modules (ingestion, structuration DuckDB, agent de recherche), testés un par un avant d'assembler le dashboard. Contrôle d'intégrité référentielle réel entre les 3 fichiers BDPM : 0 composition orpheline, 4 présentations orphelines sur 20 895, un résultat honnête obtenu sur de vraies données, pas un chiffre choisi pour la démonstration.

**Amélioration trouvée en testant** : la recherche retournait des médicaments retirés du marché avant des médicaments réellement commercialisés pour une même requête. Corrigé en priorisant les médicaments au statut "Commercialisée" dans le score de pertinence.

## Étape 4, Agent de recherche cadré

Point le plus important sur un sujet médical : l'IA ne doit jamais répondre de mémoire. Le moteur retrouve d'abord les fiches réellement pertinentes dans la base structurée (recherche lexicale, pas d'embeddings, suffisant sur un vocabulaire de noms de médicaments et substances exact), puis le prompt de synthèse interdit explicitement toute connaissance médicale externe et impose la citation du code CIS de chaque médicament mentionné. Sans clé API, l'app affiche directement les fiches sources plutôt que de bloquer la démonstration.

---

## Ce que ce projet prouve (pour un client ou une ESN)

| Compétence démontrée | Preuve dans ce projet |
|---|---|
| Gestion de données réelles, pas de mock | BDPM réelle, vérifiée par téléchargement avant codage, licence citée |
| Structuration relationnelle avec contrôle qualité | Modèle dim/fact DuckDB, intégrité référentielle mesurée, pas supposée |
| IA cadrée sur sujet sensible | Agent RAG qui refuse d'inventer, cite systématiquement sa source |
| Arbitrage technique argumenté | Stack adaptée à la contrainte de déploiement gratuit, documenté explicitement |
| Rigueur méthodologique | Bug de tri par pertinence trouvé et corrigé en testant, pas après livraison |

---

## Ma conclusion

> Je ne suis pas développeuse. Mais sur un sujet aussi sensible qu'une base de médicaments, je sais exiger qu'une IA ne réponde jamais sans preuve vérifiable, et je vérifie une source réelle avant de coder plutôt que de faire confiance à une structure supposée.

*Gisèle Metouck, Consultante Data Steward & Gouvernance*
