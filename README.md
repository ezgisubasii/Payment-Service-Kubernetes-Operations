# Payment Service Operations on Kubernetes

A small payment API that runs on Kubernetes with health checks, resource limits, secrets and load balancing across replicas. The goal of the project is the operations side, which means how the service is packaged, deployed, kept healthy and debugged.

## What is in the project

| Part | Details |
|---|---|
| Payment API | Flask app with `/pay`, `/health` and `/metrics`. Invalid input returns 400. |
| Card masking | Only the last 4 digits of a card number are written to logs. Invalid card numbers are not logged at all. Based on the PCI DSS rule that full card numbers must not be stored in plain text. |
| Container | `python:3.12-slim` image, runs as a non-root user (UID 10001). Dependencies are installed before the code is copied, so code changes do not reinstall packages. |
| Kubernetes | Namespace, Deployment with 3 replicas, NodePort Service, ConfigMap and Secret. |
| Health checks | Readiness probe keeps traffic away from pods that are not ready. Liveness probe restarts pods that stop responding. |
| Resources | CPU and memory requests and limits on every pod. |
| Security | `runAsNonRoot` on the pod. The app refuses to start without its gateway key and never logs the key. |
| Metrics | `payments_total` counter with a `status` label (success or failed), ready for Prometheus. |

## Environment

- CentOS 7.8, kernel 3.10
- minikube v1.39.0 with the none driver
- Kubernetes v1.31.0, containerd 1.6.33, Docker 26.1.4

## How to run

Build the image and import it into containerd, because Kubernetes uses containerd and cannot see Docker's images.

```bash
sudo docker build -t payment-service:1.1 app
sudo docker save payment-service:1.1 | sudo ctr -n k8s.io images import -
```

Deploy.

```bash
kubectl apply -f k8s/
kubectl get pods -n payments
```

Test.

```bash
curl -s localhost:30080/health
curl -s -X POST localhost:30080/pay -H "Content-Type: application/json" \
  -d '{"card_number":"4111111111111111","amount":100}'
curl -s localhost:30080/metrics | grep payments_total
kubectl logs -n payments -l app=payment-service --prefix
```

The logs show requests handled by different pods, and card numbers appear as `**** **** **** 1111`.

## Notes

- The Secret in `k8s/01-config.yaml` holds a demo value. In a real setup secrets would not be stored in git, a tool such as Vault or Sealed Secrets would be used instead.
- The Flask development server is used for now. It will be replaced with gunicorn.
