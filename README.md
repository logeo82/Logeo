# Motion Studio — photo vers vidéo

Prototype photo-vers-vidéo à partir de l'ancien dépôt Logeo. L'interface est reliée à un moteur de démonstration public Hugging Face via Gradio Client.

## Fonctionnalités

- Interface responsive en français.
- Import JPG/PNG/WEBP (12 Mo maximum).
- Prompt de mouvement, aperçu de la photo et lecteur vidéo MP4.
- Vérification des droits et consentement avant l'envoi.
- Endpoint serveur `POST /api/generate-video`, limites de taille et délai entre générations.
- Mode adulte désactivé.

## Moteurs IA gratuits utilisés

### Transformation photo — FLUX.2 Klein 4B
- Space public : [black-forest-labs/FLUX.2-klein-4B](https://huggingface.co/spaces/black-forest-labs/FLUX.2-klein-4B).
- API Gradio : `/infer`, appelée depuis le serveur avec `gradio_client`.
- Licence des poids du modèle : Apache-2.0, selon la [fiche officielle du modèle](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B). Cela ne remplace pas la vérification des conditions du Space public utilisé pour l'inférence.

### Photo vers vidéo — Wan 2.2
- Moteur principal : [r3gm/wan2-2-fp8da-aoti-preview2](https://huggingface.co/spaces/r3gm/wan2-2-fp8da-aoti-preview2), API Gradio `/generate_video`.
- Secours : [preSalesAIAutomation/imagetovideo](https://huggingface.co/spaces/preSalesAIAutomation/imagetovideo), API Gradio `/generate_video_sync`.
- Les appels vidéo utilisent les paramètres documentés par la signature du moteur. Le moteur principal a été corrigé pour transmettre tous les paramètres attendus, dont le modèle d'upscaling, les options de sécurité et la durée.
- La famille Wan 2.2 est publiée sous Apache-2.0 pour les variantes officielles mentionnées dans leur fiche de licence ; vérifier la fiche exacte du modèle utilisé et les conditions du Space avant tout usage commercial.

### Limites réelles du gratuit
Les Spaces ZeroGPU sont accessibles gratuitement, mais utilisent une infrastructure partagée et des quotas par utilisateur. La documentation Hugging Face indique actuellement un quota quotidien gratuit limité (par exemple, 5 minutes de GPU pour un compte gratuit), avec une file d'attente qui varie selon la demande. Ces limites peuvent évoluer. Render héberge uniquement le site/API de liaison : aucun GPU n'est hébergé sur l'ordinateur du propriétaire, et Render ne calcule pas lui-même les images ou vidéos.

Le face swap vidéo n'est pas inclus dans la voie gratuite : l'endpoint existant dépend de MuAPI et d'une clé API dont l'utilisation peut être payante. Ne pas configurer cette clé si le budget doit rester à 0 €.

**Confidentialité :** lors d'une génération, la photo et le prompt sont transmis au fournisseur du Space public pour traitement. N'envoyez pas de photo intime, sensible ou confidentielle. Les espaces publics peuvent modifier leur API, se mettre en veille, être saturés ou disparaître. Le service ne peut donc pas garantir des générations illimitées ni une disponibilité permanente.

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
