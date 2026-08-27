# Commandes du workshop

Toutes les commandes à taper, dans l'ordre. Trois parties :

1. Docker : faire tourner l'agent sur son poste
2. Kubernetes : le déployer dans un cluster
3. HPA : le faire scaler tout seul

Remplacez `sk-votre-cle` par la clé qui vous a été remise.

## Installation des outils

Docker Desktop doit déjà être lancé :

```bash
docker version
```

Installer k3d (crée un cluster Kubernetes dans Docker) :

```bash
# macOS et Linux
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash

# macOS avec Homebrew
brew install k3d
```

Installer kubectl (le client Kubernetes) :

```bash
# macOS
brew install kubectl

# Linux
curl -LO "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

Vérifier :

```bash
k3d version
kubectl version --client
```

## Partie 1 : Docker

### Récupérer l'image

Aucun build à faire, l'image est publique :

```bash
docker pull ghcr.io/denisakp/agent-app:latest
```

### Lancer le conteneur

```bash
docker run -d --name agent-app -p 8000:8000 \
  -e LLM_BASE_URL=https://r7umxvllm.denisakp.me/v1 \
  -e LLM_API_KEY=sk-votre-cle \
  -e LLM_MODEL=groq-120b \
  ghcr.io/denisakp/agent-app:latest
```

Vérifier qu'il tourne :

```bash
docker ps
docker logs agent-app
```

### Tester les trois endpoints

```bash
curl -s localhost:8000/health
curl -s localhost:8000/stats

curl -s localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "Explique Kubernetes en une phrase."}'
```

Rappelez le `/stats` après quelques `/chat` : le compteur monte, et `served_by` affiche l'identifiant du conteneur.

### Arrêter et supprimer

```bash
docker stop agent-app
docker rm agent-app
```

## Partie 2 : Kubernetes

### Créer le cluster

L'option `-p` ouvre le port 30080 du cluster vers votre machine :

```bash
k3d cluster create workshop -p "30080:30080@server:0"
```

Vérifier :

```bash
kubectl cluster-info
kubectl get nodes
```

### Créer le Secret

Le Secret n'est pas dans le dépôt : il contient votre clé, vous le créez vous-même.

```bash
kubectl create secret generic agent-secret \
  --from-literal=LLM_API_KEY=sk-votre-cle
```

Regarder ce que Kubernetes en a fait :

```bash
kubectl get secret agent-secret -o yaml
```

### Appliquer les manifestes

On les applique directement depuis GitHub, sans cloner le dépôt :

```bash
R=https://raw.githubusercontent.com/denisakp/agent-app/main/k8s

kubectl apply -f $R/configmap.yaml
kubectl apply -f $R/pvc.yaml
kubectl apply -f $R/deployment.yaml
kubectl apply -f $R/service.yaml
```

Si vous avez cloné le dépôt, depuis sa racine :

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

### Vérifier le déploiement

Le premier démarrage télécharge l'image, comptez une à trois minutes :

```bash
kubectl rollout status deployment/agent-app
kubectl get pods,svc,pvc,configmap
kubectl logs -l app=agent-app --tail=20
```

### Tester

```bash
curl -s localhost:30080/health
curl -s localhost:30080/stats

curl -s localhost:30080/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "Cest quoi un Pod ?"}'
```

Si vous avez créé le cluster sans l'option `-p`, passez par un tunnel dans un second terminal, puis utilisez `localhost:8000` :

```bash
kubectl port-forward svc/agent-app 8000:80
```

### Passer à 5 replicas

```bash
kubectl scale deployment/agent-app --replicas=5
kubectl get pods -o wide
```

Le Service répartit les appels, `served_by` change à chaque fois :

```bash
for i in $(seq 1 10); do curl -s localhost:30080/stats; echo; done
```

Envoyer des messages, puis relire les compteurs :

```bash
for i in $(seq 1 8); do
  curl -s -o /dev/null localhost:30080/chat \
    -H 'Content-Type: application/json' \
    -d '{"message":"Dis un mot."}'
done

for i in $(seq 1 10); do curl -s localhost:30080/stats; echo; done | sort -u
```

Chaque Pod affiche un total différent : le compteur vit en mémoire, dans le Pod, et n'est partagé avec personne.

### Revenir à 1 replica

```bash
kubectl scale deployment/agent-app --replicas=1
```

## Partie 3 : HPA

L'autoscaler ajoute et retire des Pods selon la charge CPU.

```bash
kubectl apply -f $R/hpa.yaml
```

Regarder son état, la colonne TARGETS met environ une minute à s'afficher :

```bash
kubectl get hpa
kubectl top pods
```

Suivre en direct dans un premier terminal :

```bash
kubectl get hpa -w
```

Générer de la charge dans un second terminal :

```bash
for w in 1 2 3 4 5 6; do
  (for i in $(seq 1 4000); do curl -s -o /dev/null localhost:30080/health; done) &
done
```

Le nombre de replicas monte quand le CPU dépasse 50 pour cent, puis redescend quelques minutes après la fin de la charge.

```bash
kubectl get pods
kubectl describe hpa agent-app
```

## Nettoyage

```bash
k3d cluster delete workshop
docker rm -f agent-app
```

## En cas de problème

Le Pod ne démarre pas :

```bash
kubectl describe pod -l app=agent-app
kubectl logs -l app=agent-app
```

`/chat` renvoie une erreur 502 : la passerelle est injoignable ou la clé est invalide. `/health` et `/stats` continuent de répondre, la suite du TP fonctionne quand même.

Le port 30080 ne répond pas : le cluster a été créé sans l'option `-p`. Utilisez `kubectl port-forward` (voir partie 2) ou recréez le cluster.

Vérifier la configuration réellement reçue par le Pod :

```bash
kubectl exec deploy/agent-app -- env | grep -E 'LLM_BASE_URL|LLM_MODEL'
```

Ne faites pas afficher `LLM_API_KEY` : la commande écrirait votre clé en clair à l'écran.
