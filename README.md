# Motion Studio — photo vers vidéo

Prototype photo-vers-vidéo à partir de l'ancien dépôt Logeo. L'interface est reliée à un moteur de démonstration public Hugging Face via Gradio Client.

## Fonctionnalités

- Interface responsive en français.
- Import JPG/PNG/WEBP (12 Mo maximum).
- Prompt de mouvement, aperçu de la photo et lecteur vidéo MP4.
- Vérification des droits et consentement avant l'envoi.
- Endpoint serveur `POST /api/generate-video`, limites de taille et délai entre générations.
- Mode adulte désactivé.

## Moteur vidéo

Le prototype appelle le Space public [yuknassty/wan2-2-image-to-video](https://huggingface.co/spaces/yuknassty/wan2-2-image-to-video), basé sur Wan 2.2. Ce service externe peut être occupé, changer d'API, être mis hors ligne ou imposer des limites de quota. L'intégration doit être testée après déploiement.

**Confidentialité :** lorsqu'une génération est lancée, la photo et le prompt sont transmis au Space Hugging Face public pour traitement. N'envoyez pas de photo intime, sensible ou confidentielle. Vérifier les conditions d'utilisation et la licence du modèle avant tout usage commercial. Ce prototype ne doit pas être présenté comme un service de génération garanti ou illimité.

## Configuration facultative du compte Hugging Face

Le service peut être appelé sans jeton, mais l'accès anonyme peut être davantage limité. Pour associer les appels au compte du propriétaire :

1. Créer un jeton Hugging Face avec les droits minimaux nécessaires.
2. Ajouter le jeton dans les variables d'environnement de l'hébergement sous le nom `HF_TOKEN`.
3. Ne jamais coller ce jeton dans le code, dans GitHub ou dans le navigateur.

Le jeton n'est pas requis pour afficher le site. Ne jamais transmettre le jeton dans une conversation.

## Démarrer localement

Python 3.11+ recommandé.

```bash
pip install -r requirements.txt
python app.py
```

Puis ouvrir http://localhost:8080.

## Déploiement gratuit sans Railway

Le fichier `render.yaml` configure un service web Render sur le plan gratuit. Dans Render, créer un Blueprint à partir de ce dépôt et vérifier que le plan sélectionné est bien gratuit avant de confirmer.

Les services gratuits peuvent s'endormir après une période d'inactivité et leur stockage local n'est pas persistant. Le moteur vidéo reste hébergé par Hugging Face : Render ne fournit pas de GPU à ce projet.

## Sécurité et limites

- Utiliser uniquement des images que vous êtes autorisé à envoyer et animer.
- Ne pas utiliser de photos de mineurs ni d'images sexuelles de personnes réelles sans consentement explicite.
- Le mode adulte est désactivé tant qu'un moteur et ses conditions ne sont pas validés.
- Les quotas gratuits peuvent changer et ne garantissent aucune disponibilité ni génération illimitée.
- Avant un lancement public ou commercial, ajouter une politique de confidentialité, des conditions d'utilisation, une gestion des demandes de retrait, une protection contre les abus et une vérification juridique des licences et conditions du fournisseur.
