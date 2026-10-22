# Motion Studio (ex-Logeo)

Prototype photo-vers-vidéo à partir de l'ancien dépôt Logeo. L'interface a été remplacée, mais le moteur de génération vidéo IA n'est **pas encore intégré**.

## Ce qui fonctionne
- Interface responsive en français.
- Import JPG/PNG/WEBP et aperçu local dans le navigateur.
- Description du mouvement, choix de style et de durée.
- Vérification des droits/consentement avant de préparer une demande.
- Aucun fichier photo n'est envoyé par cette interface de démonstration.

## Ce qui n'est pas encore implémenté
- Génération IA réelle, file d'attente, stockage sécurisé, comptes, téléchargement MP4.
- La prévisualisation animée est un effet CSS local, pas une vidéo générée.
- Aucun contenu adulte n'est généré par cette version.

## Pourquoi le budget de 0 € change le choix technique
Un vrai moteur image-vers-vidéo a besoin d'un GPU. Wan 2.2 est une option open source à étudier, mais ses variantes demandent une machine GPU compatible; ce n'est pas réaliste de promettre une génération illimitée et fiable sur un hébergement gratuit. Voir le dépôt officiel : https://github.com/Wan-Video/Wan2.2

La voie gratuite pour démarrer est de garder l'interface et de tester ensuite le modèle localement sur un ordinateur disposant d'un GPU adapté, ou d'un quota de démonstration gratuit dont les conditions autorisent expressément les usages envisagés. Les quotas gratuits ne sont pas garantis et peuvent changer.

## Lancer localement
Python 3.11+ recommandé.

```bash
pip install -r requirements.txt
python start.py
```

Puis ouvrir http://localhost:8080.

## Déploiement web gratuit (sans Railway)
Le fichier `render.yaml` prépare un service web Render gratuit pour l'interface. Dans Render, créer un nouveau Blueprint à partir de ce dépôt et vérifier que l'offre sélectionnée est bien gratuite avant de confirmer. Les services gratuits peuvent s'endormir et leur stockage local n'est pas persistant. Vérifier les conditions du fournisseur avant d'accepter des images sensibles ou du contenu adulte.

Important : ce déploiement hébergerait seulement le prototype web; il ne fournit pas de GPU ni de génération vidéo IA. Pour un produit public traitant des images intimes, ajouter avant ouverture : règles d'usage, contrôle d'âge approprié, gestion des demandes de retrait, politique de confidentialité, sécurité du stockage, limites d'usage et mécanismes anti-abus. Interdire strictement les mineurs, les images sexuelles de personnes réelles sans consentement explicite et tout contenu illégal.

## Sécurité
Ne jamais ajouter de clés API ou de mots de passe au dépôt Git. Ne pas utiliser de photos sensibles pendant la phase prototype.