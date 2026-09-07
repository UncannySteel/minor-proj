# RepoMind — AI-Powered GitHub Engineering Intelligence

A dark-first developer intelligence platform where users connect GitHub, select repositories, and get issue/PR analytics, AI predictions, repository intelligence, and research-grade model evaluation.

## Core Decisions

- **Per-user GitHub sign-in:** Lovable Cloud auth + per-user GitHub OAuth. Tokens remain server-side.
- **Prediction sources:**
  - Demo Mode → deterministic seeded predictions, labelled `DEMO DATA`.
  - Real repositories → Lovable AI predictions/explanations, labelled `EXPERIMENTAL AI`.
  - Never claim predictions come from the trained RepoMind research model.
- **Research evaluation:** Model Evaluation shows empty states until real experiment data is connected. Never invent metrics.
- **Creation-time feature contract:** Predictions use only title, body, author metadata, creation timestamp, and repository state available at creation. Every prediction includes a "Data available at creation" audit panel. Post-hoc analysis is explicitly separate.

## Design

- Dark charcoal/near-black UI
- White typography
- Thin 1px borders
- Restrained blue→violet accents
- Dense but spacious layouts
- GitHub × Linear × Vercel aesthetic
- Custom RepoMind mark based on stacked repository layers
- Recharts, shadcn, skeletons, empty/error states, sonner toasts

## Application

### Public & Shell

Landing page:
- Hero
- "What RepoMind Understands"
- Architecture strip
- "Built for Real Engineering Teams"
- Connect GitHub
- Explore Demo

App shell:
- Overview
- Repositories
- Issues
- Pull Requests
- Analytics
- AI Insights
- Contributors
- Predictions
- Model
- Model Evaluation
- Settings

Top bar:
- Repository selector
- `/` command palette
- Sync
- Notifications
- Profile

Maintain global mode and repository mode with breadcrumbs and persistent repository context.

### Onboarding

`Sign in → Connect GitHub → Select repositories → Initial sync → Dashboard`

Repository picker supports:
- Search
- Filtering
- Sorting
- Multi-select
- Select all

### Overview

Include:
- Repository / issue / PR / contributor KPIs
- Engineering activity chart: 7D / 30D / 90D / 1Y
- Issue type distribution
- Priority distribution
- Resolution-time distribution
- Repository health score
- Per-dimension explanations

### Repository

Tabs:
- Overview
- Issues
- Pull Requests
- Commits
- Contributors
- AI Intelligence

### Issues

Sortable/filterable issue table with:
- Type
- Priority
- Status
- Author
- Assignee
- Age
- Predicted resolution
- AI confidence

Issue Intelligence page:
- Original GitHub issue
- Category prediction
- Priority prediction
- Resolution estimate
- Lifecycle risk
- Confidence
- Explanation/contribution bars
- Creation-time audit
- Similar issues
- AI actions

### Other Core Pages

**Pull Requests**
- PR activity, age, status and merge analytics.

**Contributors**
- Contributions, issues, PRs, reviews and activity.

**Analytics**
- Issue, PR, contributor and repository-health analytics.

**AI Insights**
Each insight contains:
- Finding
- Evidence
- Confidence
- Recommended action

**Predictions**
- Prediction table
- Re-run
- Compare
- CSV export
- Detail drawer
- Model version

**Model**
Visualize:

`GitHub Issue → Text + Creation Metadata → Transformer + Metadata Encoder → Shared Representation → Task Heads → Category + Priority + Resolution Time → Confidence + Explanation`

**Model Evaluation**
Track:
- TF-IDF + Logistic Regression
- TF-IDF + SVM
- Metadata-only
- BiGRU
- Transformer text-only
- Transformer + metadata
- Multi-task Transformer + metadata

Metrics:
- Macro-F1
- Weighted-F1
- Precision
- Recall
- MCC
- MAE
- Calibration
- Confusion matrices

Evaluation modes:
- Random split
- Temporal split
- Unseen-repository split

Ablations:
- Text-only
- Metadata-only
- Fusion
- Single-task
- Multi-task

Also track:
- Latency
- Memory
- Throughput
- Model size
- Explainability

**Cross-Repository Intelligence**
- Compare repositories
- Aggregate metrics
- Train/test repository views
- Unseen-repository evaluation

**Settings**
- GitHub connection
- Repository selection
- Sync settings
- AI model/prediction settings
- Confidence threshold
- Research Mode

Research Mode reveals:
- Model versions
- Experiments
- Dataset metadata
- Split strategy
- Feature contract
- Ablations

## Demo Mode

Provide a fully functional deterministic demo from day one.

Seed repositories:
- `RepoMind-Core`
- `RepoMind-API`
- `RepoMind-Web`

Include realistic:
- Issues
- Pull Requests
- Commits
- Contributors
- Predictions
- Analytics

Use a fixed seed so results remain stable and explainable.

Display a persistent `DEMO MODE` badge.

Demo data must live in a separate namespace and never mix with real GitHub records.

## Technical Architecture

### Stack

- TanStack Start
- React 19
- Tailwind v4
- shadcn/ui
- Recharts
- TanStack Query
- TypeScript

Use route loaders with `ensureQueryData`.

### Backend

Lovable Cloud:
- PostgreSQL
- Authentication
- RLS

Core tables:

`profiles`
`github_connections`
`repositories`
`repository_selections`
`issues`
`issue_labels`
`pull_requests`
`commits`
`contributors`
`issue_predictions`
`prediction_explanations`
`repository_metrics`
`ai_insights`
`model_versions`
`experiments`
`experiment_metrics`
`sync_jobs`
`audit_logs`

Security:
- Explicit GRANTs
- RLS scoped to `auth.uid()`
- No anonymous access
- Encrypted GitHub connection credentials
- Tokens never exposed to clients

### GitHub

Use Lovable's per-user GitHub App User Connector.

Server-side handlers perform GitHub API operations.

Sync:
- Repositories
- Issues
- Labels
- Milestones
- Pull Requests
- Commits
- Contributors

Record sync counts/errors in `sync_jobs`.

If GitHub does not provide a field, display `Not available`; never fabricate it.

## Prediction Architecture

Create a single `PredictionProvider` interface:

```text
classify()
priority()
resolutionTime()
explain()
similar()
```

Implement:
1. `demo`
2. `llm`
3. `repomind` — future FastAPI inference client

The UI must remain independent of the prediction provider so the real RepoMind model can replace the experimental provider without redesign.

## Server API

Expose server functions corresponding to:

```text
repositories
repository detail
issues
pull requests
issue detail
analyze
prediction
analytics
insights
models
experiments
```

Use strongly typed shared domain models in:

`src/types/`

Add unique route metadata using `head()`.

## Build Phases

### Phase 1
Authentication, GitHub connection, repository picker and application shell.

### Phase 2
Repository dashboard, Issues, PRs, Contributors and Analytics.

### Phase 3
Issue Intelligence, AI Predictions, Insights and Similar Issues.

### Phase 4
Model architecture, Evaluation and Cross-Repository research mode.

### Phase 5
Real FastAPI RepoMind inference service and production ML integration.

## Critical Scope Rule

Build the complete application architecture and functional Demo Mode now, but **do not pretend the research model exists**.

Use:
- `DEMO DATA` for deterministic demo predictions.
- `EXPERIMENTAL AI` for Lovable AI predictions.
- `REPO-MIND MODEL` only after the real FastAPI inference service is connected.

Model Evaluation must display:

**"No experiment data connected."**

until actual results are uploaded.

Phase 5 is therefore the documented integration seam for the future trained RepoMind model.
