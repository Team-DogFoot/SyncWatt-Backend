# K8S DB 구축 및 환경변수 최신화 구현 계획

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `esgo-db` 매니페스트를 참조하여 `syncwatt-db`를 K8s에 구축하고, 추가된 환경변수(DB, 기상청 API)를 로컬, 매니페스트(템플릿/실제값), 런타임 환경에 모두 반영합니다.

**Architecture:** 
1. `dog-foot-k8s-manifests` 레포 내 `prod/syncwatt-db` 생성 (PostgreSQL StatefulSet).
2. `prod/syncwatt` 내 `deployment.yaml` 및 `secret.template.yaml` 업데이트.
3. 로컬 `.env` 및 SealedSecrets를 통한 런타임 Secret 업데이트.

**Tech Stack:** Kubernetes (K3s), Kustomize, SealedSecrets, PostgreSQL, GitHub Actions.

---

### Task 1: 매니페스트 레포 내 DB 서비스 구축 (`esgo-db` 참조)

**Files:**
- Create: `dog-foot-k8s-manifests/prod/syncwatt-db/postgres-statefulset.yaml`
- Create: `dog-foot-k8s-manifests/prod/syncwatt-db/postgres-configmap.yaml`
- Create: `dog-foot-k8s-manifests/prod/syncwatt-db/postgres-secret.yaml`
- Modify: `dog-foot-k8s-manifests/prod/syncwatt-db/kustomization.yaml`

**Step 1: StatefulSet 및 Service 작성**
`esgo-db` 설정을 복사하되 name을 `syncwatt-postgres`, namespace를 `syncwatt-prod`로 변경. storageClassName 등 노드 설정 확인.

**Step 2: ConfigMap 작성**
PostgreSQL 설정(timezone=Asia/Seoul 등) 반영.

**Step 3: Secret 작성 (템플릿)**
`postgres-db`, `postgres-user`, `postgres-password` 초기값 설정.

---

### Task 2: 백엔드 환경변수 최신화 (매니페스트 & 로컬)

**Files:**
- Modify: `SyncWatt-Backend/.env`
- Modify: `dog-foot-k8s-manifests/prod/syncwatt/secret.template.yaml`
- Modify: `dog-foot-k8s-manifests/prod/syncwatt/deployment.yaml`

**Step 1: 로컬 .env 업데이트**
`KMA_API_KEY`, `DATABASE_URL` 등 누락된 변수 최종 확인 및 정리.

**Step 2: 매니페스트 Secret Template 업데이트**
`KMA_API_KEY`, `DATABASE_URL`, `POSTGRES_USER` 등 신규 변수 추가.

**Step 3: deployment.yaml 업데이트**
신규 환경변수를 Container Env에 매핑.

---

### Task 3: 런타임 Secret 반영 (SealedSecrets)

**Files:**
- Create: `SyncWatt-Backend/secret.yaml` (Temporary, GitIgnore 확인)
- Modify: `dog-foot-k8s-manifests/prod/syncwatt/sealed-secret.yaml`

**Step 1: 로컬에서 Secret 생성 (Dry-run)**
`kubectl create secret generic syncwatt-secret --from-env-file=.env --dry-run=client -o yaml > secret.yaml`

**Step 2: SealedSecret 생성**
`kubeseal < secret.yaml > sealed-secret.yaml` 수행 후 매니페스트 레포로 이동.

---

### Task 4: 최종 커밋, 푸쉬 및 배포 추적

**Step 1: SyncWatt-Backend 작업물 커밋/푸쉬**
`git add .`, `git commit -m "feat: update env and ci/cd config"`, `git push origin main`

**Step 2: 매니페스트 레포 작업물 커밋/푸쉬**
`git add .`, `git commit -m "chore: setup syncwatt-db and update secrets"`, `git push origin main`

**Step 3: GitHub Actions 및 ArgoCD 모니터링**
빌드 성공 및 K8s 파드 정상 기동 확인.

---

### Task 5: SMP 데이터 적재 (운영 환경)

**Step 1: 운영 DB 연결 확인**
`kubectl exec` 또는 포트 포워딩을 통해 DB 접속 확인.

**Step 2: seed_smp.py 실행**
운영 환경에서 SMP 데이터 적재 확인 (필요시 임시 파드 생성하여 실행).
