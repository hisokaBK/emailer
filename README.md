# Auto Candidature

Auto Candidature est une application locale de recherche et d'envoi de candidatures, conçue pour aider un candidat marocain à organiser ses candidatures et à envoyer des emails personnalisés depuis une interface dédiée.

## Vue d'ensemble

L'application localise les offres d'emploi, extrait les informations clés du CV, stocke les résultats dans SQLite, puis génère des emails personnalisés en français avec Google Gemini. Une fois validés, les emails sont envoyés via l'API Gmail avec OAuth 2.0.

## Structure du projet

- `app.py` : point d'entrée Streamlit.
- `config/` : configuration générale et variables d'environnement.
- `pages/` : pages Streamlit dans un style multipage.
- `services/` : logique métier (profil, PDF, Excel, Gmail, emailing, IA, etc.).
- `sources/` : intégrations de sources d'offres.
- `database/` : base SQLite, modèles et repositories.
- `data/` : stockage local de JSON de profil et de contexte.
- `uploads/` : CV, lettres de motivation et fichiers Excel.
- `credentials/` : credentials OAuth et tokens Gmail.
- `exports/` : exports de résultats.
- `logs/` : journaux applicatifs.
- `tests/` : tests automatiques.

## Démarrage rapide

1. Créer un environnement virtuel.
2. Installer les dépendances : `pip install -r requirements.txt`
3. Copier `.env.example` vers `.env` et remplir les valeurs.
4. Lancer : `streamlit run app.py`

## Configuration Gemini

Renseigner au minimum :
- `GEMINI_API_KEY_1`
- `GEMINI_MODEL`

Les clés sont lues depuis `.env` et les valeurs sensibles ne doivent pas être versionnées.

## Configuration Gmail

1. Créer un projet Google Cloud.
2. Activer l'API Gmail.
3. Créer des identifiants OAuth desktop.
4. Télécharger les credentials JSON dans `credentials/google_credentials.json`.
5. Lancer l'application et autoriser le compte Google.

Les permissions minimales demandées sont les permissions Gmail `gmail.send`.

## Sécurité

- Les clés API et les tokens OAuth restent locaux.
- Les documents PDFs sont stockés et ne sont pas envoyés à Gemini sans nécessité.
- Les données privées restent dans le dossier local du projet.

## Limites actuelles

- Les sources d'offres marocaines sont intégrées comme connecteurs structurés et prêtes à être enrichis.
- La génération Gemini se fait en mode sûr avec fallback local si la clé n'est pas valide.
- Les envois Gmail demandent une configuration Google réelle sur la machine de l'utilisateur.

## Utilisation du MVP

1. Dans **Parametres**, televerser le CV et la lettre de motivation, puis completer le profil et la signature.
2. Dans **Chercheur d'offres**, rechercher des offres et enregistrer celles a suivre.
3. Dans **Générateur d'emails**, choisir le type de candidature et le poste visé. Pour une offre sélectionnée, le type (stage/emploi) et l'intitulé réel sont repris automatiquement.
4. Pour une candidature spontanée, générer un email individuel ou importer un fichier Excel, associer ses colonnes, puis ajuster le type et le poste pour chaque entreprise avant de générer le lot.
5. Relire le corps, enregistrer le brouillon ou l'envoyer explicitement après avoir connecté Gmail. Le type choisi est conservé dans le suivi SQLite.

Les envois ne sont jamais automatiques. Les PDF restent locaux et sont joints uniquement lors d'un envoi Gmail declenche par l'utilisateur.

Les instructions destinées à Gemini distinguent les candidatures spontanées de stage, d'emploi ou de poste précis des réponses à de vraies offres. Les réponses aux offres Excel nécessitent un titre et une description d'offre réels. L'objet reste celui configuré dans **Paramètres** et n'est jamais généré par Gemini. Le contexte de lettre de motivation se configure dans **Paramètres** et seuls les éléments saisis dans ce contexte sont transmis, pas le texte complet du PDF.

## Tests

Exécuter :

```bash
pytest -q
```
