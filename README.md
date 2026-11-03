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

1. Créer un environnement virtuel, si souhaité.
2. Installer les dépendances : `py -m pip install -r requirements.txt`
3. Copier `.env.example` vers `.env` et remplir les valeurs nécessaires.
4. Lancer : `py -m streamlit run app.py` ou exécuter `start.bat`.

## Configuration Gemini

Renseigner au minimum :
- `GEMINI_API_KEY_1`
- `GEMINI_MODEL`

Les clés sont lues depuis `.env` et les valeurs sensibles ne doivent pas être versionnées.

## Configuration Gmail

Le projet Google Cloud et l'API Gmail étant déjà configurés, conserver le fichier OAuth Desktop téléchargé dans `credentials/google_credentials.json`. L'application utilise ce fichier existant et ne crée ni ne modifie aucun client OAuth.

1. Installer les dépendances : `py -m pip install -r requirements.txt`.
2. Vérifier la présence de `credentials/google_credentials.json`.
3. Démarrer l'application : `py -m streamlit run app.py`.
4. Ouvrir **Paramètres > Gmail**, puis cliquer explicitement sur **Connecter Gmail**.
5. Dans le navigateur local, choisir le compte Google et autoriser l'envoi. Le jeton est conservé dans `credentials/gmail_token.json`.
6. Vérifier que la page affiche **connecté**. Aucun email n'est envoyé pendant l'authentification.

Le flux d'autorisation ouvre un navigateur sur l'ordinateur qui exécute Streamlit et attend le retour OAuth local sur `localhost`. Il est conçu pour un lancement local sur le PC de l'utilisateur, pas pour un déploiement Streamlit distant ou sans navigateur. Si l'application OAuth est en mode **External / Testing**, Google peut faire expirer le refresh token après sept jours ; dans ce cas, déconnecter puis reconnecter Gmail. Une révocation Google peut aussi être faite depuis les paramètres de sécurité du compte Google.

Seul le scope `https://www.googleapis.com/auth/gmail.send` est demandé. L'adresse du compte n'est pas affichée, car l'application ne demande pas de permission supplémentaire pour lire le profil Gmail.

Les variables `GMAIL_CREDENTIALS_PATH` et `GMAIL_TOKEN_PATH` peuvent remplacer les chemins par défaut. Les chemins relatifs sont résolus depuis le dossier du projet. Les valeurs `GOOGLE_CLIENT_ID` et `GOOGLE_CLIENT_SECRET` ne sont pas nécessaires au flux : le fichier OAuth Desktop téléchargé est la source de configuration.

## Sécurité

- Les clés API et les tokens OAuth restent locaux.
- Tout le dossier `credentials/`, y compris les identifiants et jetons Google, est exclu de Git.
- Le jeton Gmail est écrit de manière atomique et avec des permissions restreintes lorsqu'elles sont prises en charge par le système.
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

## Dépannage Gmail

- **Credentials introuvables ou invalides** : vérifier que le JSON OAuth Desktop d'origine existe sous `credentials/google_credentials.json`. Ne pas le copier dans le dépôt ni le coller dans les logs.
- **Utilisateur de test non autorisé** : ajouter le compte Google utilisé à la liste **Test users** de l'écran de consentement OAuth, ou publier l'application selon les exigences Google.
- **API non activée ou accès refusé** : vérifier l'activation de Gmail API et le scope d'envoi demandé.
- **Jeton expiré ou révoqué** : dans Paramètres, cliquer sur **Déconnecter Gmail**, puis **Connecter Gmail**.
- **Erreur réseau** : vérifier l'accès internet et relancer explicitement l'action.

La déconnexion supprime uniquement le jeton local de l'application ; pour retirer aussi l'accès côté Google, révoquer l'application depuis les paramètres du compte Google.

## Tests

Exécuter :

```bash
pytest -q
```
