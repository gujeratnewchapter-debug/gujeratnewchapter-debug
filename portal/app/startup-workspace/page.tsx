'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Target } from 'lucide-react';
import { InnovationLoader } from '@/components/InnovationLoader';
import { useAuth } from '@/lib/auth-context';
import { useFeatureFlagStatus } from '@/lib/featureFlags';
import {
  createStartupMilestone,
  createStartupProject,
  getStartupProjects,
  updateStartupMilestone,
  updateStartupProject,
} from '@/lib/api';
import type {
  StartupMilestone,
  StartupMilestoneStatus,
  StartupProject,
  StartupProjectPayload,
  StartupProjectStage,
  StartupProjectStatus,
} from '@/lib/api';
import { useI18n } from '@/lib/i18n';
import type { TranslationKey } from '@/lib/translations';

type WorkspaceErrorKey = Extract<
  TranslationKey,
  'workspaceLoadError' | 'workspaceSaveError' | 'milestoneUpdateError'
>;

const EMPTY_PROJECT: StartupProjectPayload = {
  title: '',
  description: '',
  industry: '',
  stage: 'idea',
  status: 'active',
  problem: '',
  solution: '',
  target_market: '',
  value_proposition: '',
  business_model: '',
  next_steps: '',
};

const PROJECT_STAGES: { value: StartupProjectStage; label: TranslationKey }[] = [
  { value: 'idea', label: 'stageIdea' },
  { value: 'validation', label: 'stageValidation' },
  { value: 'mvp', label: 'stageMvp' },
  { value: 'launch', label: 'stageLaunch' },
  { value: 'growth', label: 'stageGrowth' },
];

const PROJECT_STATUSES: { value: StartupProjectStatus; label: TranslationKey }[] = [
  { value: 'active', label: 'active' },
  { value: 'paused', label: 'paused' },
  { value: 'completed', label: 'completed' },
];

const MILESTONE_STATUSES: { value: StartupMilestoneStatus; label: TranslationKey }[] = [
  { value: 'not_started', label: 'notStarted' },
  { value: 'in_progress', label: 'inProgress' },
  { value: 'completed', label: 'completed' },
];

function projectDraft(project: StartupProject): StartupProjectPayload {
  return {
    title: project.title,
    description: project.description,
    industry: project.industry,
    stage: project.stage,
    status: project.status,
    problem: project.problem,
    solution: project.solution,
    target_market: project.target_market,
    value_proposition: project.value_proposition,
    business_model: project.business_model,
    next_steps: project.next_steps,
  };
}

export default function StartupWorkspacePage() {
  const { isBackendAuthenticated, isLoading } = useAuth();
  const { enabled: startupToolsEnabled, loading: featureFlagsLoading } = useFeatureFlagStatus(
    'startup_tools',
    isBackendAuthenticated,
  );
  const { t } = useI18n();
  const router = useRouter();
  const [projects, setProjects] = useState<StartupProject[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<number | null>(null);
  const [draft, setDraft] = useState<StartupProjectPayload>(EMPTY_PROJECT);
  const [milestoneDraft, setMilestoneDraft] = useState({ title: '', details: '', due_date: '' });
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [savingProject, setSavingProject] = useState(false);
  const [savingMilestone, setSavingMilestone] = useState(false);
  const [savingMilestoneId, setSavingMilestoneId] = useState<number | null>(null);
  const [error, setError] = useState<WorkspaceErrorKey | null>(null);
  const [notice, setNotice] = useState('');

  useEffect(() => {
    if (!isLoading && !isBackendAuthenticated) router.push('/');
  }, [isLoading, isBackendAuthenticated, router]);

  useEffect(() => {
    if (!isLoading && isBackendAuthenticated && !featureFlagsLoading && !startupToolsEnabled) {
      router.replace('/dashboard');
    }
  }, [featureFlagsLoading, isBackendAuthenticated, isLoading, router, startupToolsEnabled]);

  useEffect(() => {
    if (!isBackendAuthenticated || featureFlagsLoading || !startupToolsEnabled) return;
    let active = true;
    setLoadingProjects(true);
    getStartupProjects()
      .then(({ data }) => {
        if (!active) return;
        setProjects(data);
        if (data.length) {
          setActiveProjectId(data[0].id);
          setDraft(projectDraft(data[0]));
        }
      })
      .catch((requestError) => {
        console.error('Failed to load startup projects:', requestError);
        if (active) setError('workspaceLoadError');
      })
      .finally(() => {
        if (active) setLoadingProjects(false);
      });
    return () => {
      active = false;
    };
  }, [featureFlagsLoading, isBackendAuthenticated, startupToolsEnabled]);

  const activeProject = projects.find((project) => project.id === activeProjectId) ?? null;

  function startNewProject() {
    setActiveProjectId(null);
    setDraft(EMPTY_PROJECT);
    setMilestoneDraft({ title: '', details: '', due_date: '' });
    setError(null);
    setNotice('');
  }

  function selectProject(project: StartupProject) {
    setActiveProjectId(project.id);
    setDraft(projectDraft(project));
    setError(null);
    setNotice('');
  }

  function updateProjectField<K extends keyof StartupProjectPayload>(
    field: K,
    value: StartupProjectPayload[K],
  ) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  async function handleSaveProject(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingProject(true);
    setError(null);
    setNotice('');
    try {
      const response = activeProjectId
        ? await updateStartupProject(activeProjectId, draft)
        : await createStartupProject(draft);
      const savedProject = response.data;
      setProjects((current) => (
        current.some((project) => project.id === savedProject.id)
          ? current.map((project) => project.id === savedProject.id ? savedProject : project)
          : [savedProject, ...current]
      ));
      setActiveProjectId(savedProject.id);
      setDraft(projectDraft(savedProject));
      setNotice(t(activeProjectId ? 'projectUpdated' : 'projectCreated'));
    } catch (requestError) {
      console.error('Failed to save startup project:', requestError);
      setError('workspaceSaveError');
    } finally {
      setSavingProject(false);
    }
  }

  async function handleAddMilestone(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeProject) return;
    setSavingMilestone(true);
    setError(null);
    setNotice('');
    try {
      const response = await createStartupMilestone({
        project: activeProject.id,
        title: milestoneDraft.title,
        details: milestoneDraft.details,
        due_date: milestoneDraft.due_date || null,
        status: 'not_started',
        order: activeProject.milestones.length,
      });
      setProjects((current) => current.map((project) => (
        project.id === activeProject.id
          ? { ...project, milestones: [...project.milestones, response.data] }
          : project
      )));
      setMilestoneDraft({ title: '', details: '', due_date: '' });
    } catch (requestError) {
      console.error('Failed to create startup milestone:', requestError);
      setError('workspaceSaveError');
    } finally {
      setSavingMilestone(false);
    }
  }

  async function handleMilestoneStatusChange(milestone: StartupMilestone, status: StartupMilestoneStatus) {
    setSavingMilestoneId(milestone.id);
    setError(null);
    try {
      const response = await updateStartupMilestone(milestone.id, { status });
      setProjects((current) => current.map((project) => (
        project.id === response.data.project
          ? {
            ...project,
            milestones: project.milestones.map((item) => item.id === milestone.id ? response.data : item),
          }
          : project
      )));
    } catch (requestError) {
      console.error('Failed to update startup milestone:', requestError);
      setError('milestoneUpdateError');
    } finally {
      setSavingMilestoneId(null);
    }
  }

  if (isLoading || !isBackendAuthenticated || featureFlagsLoading || !startupToolsEnabled || loadingProjects) {
    return <div className="container section"><InnovationLoader label={t('loadingProjects')} /></div>;
  }

  return (
    <div className="container section">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, marginBottom: 8 }}>{t('startupWorkspace')}</h1>
        <p style={{ color: 'var(--text-muted)', margin: 0 }}>{t('workspaceDescription')}</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: 20, alignItems: 'start' }}>
        <aside className="card" style={{ padding: 18 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 14 }}>
            <h2 style={{ fontSize: 18, margin: 0 }}>{t('yourProjects')}</h2>
            <button className="btn btn-primary" type="button" onClick={startNewProject} aria-label={t('newProject')}>
              <Plus size={15} /> {t('newProject')}
            </button>
          </div>
          {projects.length === 0 && <p style={{ color: 'var(--text-muted)' }}>{t('noProjects')}</p>}
          <div style={{ display: 'grid', gap: 8 }}>
            {projects.map((project) => (
              <button
                key={project.id}
                className="btn"
                type="button"
                onClick={() => selectProject(project)}
                aria-pressed={activeProjectId === project.id}
                style={{
                  display: 'grid',
                  textAlign: 'left',
                  gap: 4,
                  background: activeProjectId === project.id ? 'var(--surface-2)' : 'transparent',
                  borderColor: activeProjectId === project.id ? 'var(--brand)' : 'var(--border)',
                }}
              >
                <strong>{project.title}</strong>
                <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                  {t(PROJECT_STAGES.find((stage) => stage.value === project.stage)?.label ?? 'stageIdea')} · {t(PROJECT_STATUSES.find((status) => status.value === project.status)?.label ?? 'active')}
                </span>
              </button>
            ))}
          </div>
        </aside>

        <main style={{ display: 'grid', gap: 20 }}>
          {!activeProject && projects.length > 0 && activeProjectId === null && !draft.title && (
            <div className="card" style={{ padding: 20, color: 'var(--text-muted)' }}>{t('chooseProject')}</div>
          )}
          {error && <p role="alert" className="card" style={{ color: 'var(--danger)', margin: 0 }}>{t(error)}</p>}
          {notice && <p role="status" className="card" style={{ color: 'var(--brand)', margin: 0 }}>{notice}</p>}

          <form className="card" onSubmit={handleSaveProject} style={{ padding: 20, display: 'grid', gap: 14 }}>
            <h2 style={{ fontSize: 18, margin: 0 }}>{activeProject ? activeProject.title : t('newProject')}</h2>
            <label style={{ display: 'grid', gap: 6, fontSize: 13 }}>
              <span>{t('projectName')}</span>
              <input className="input" maxLength={160} required value={draft.title} onChange={(event) => updateProjectField('title', event.target.value)} />
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
              <label style={{ display: 'grid', gap: 6, fontSize: 13 }}>
                <span>{t('industry')}</span>
                <input className="input" maxLength={100} value={draft.industry} onChange={(event) => updateProjectField('industry', event.target.value)} />
              </label>
              <label style={{ display: 'grid', gap: 6, fontSize: 13 }}>
                <span>{t('startupStage')}</span>
                <select className="input" value={draft.stage} onChange={(event) => updateProjectField('stage', event.target.value as StartupProjectStage)}>
                  {PROJECT_STAGES.map((stage) => <option key={stage.value} value={stage.value}>{t(stage.label)}</option>)}
                </select>
              </label>
              <label style={{ display: 'grid', gap: 6, fontSize: 13 }}>
                <span>{t('projectStatus')}</span>
                <select className="input" value={draft.status} onChange={(event) => updateProjectField('status', event.target.value as StartupProjectStatus)}>
                  {PROJECT_STATUSES.map((status) => <option key={status.value} value={status.value}>{t(status.label)}</option>)}
                </select>
              </label>
            </div>
            <label style={{ display: 'grid', gap: 6, fontSize: 13 }}>
              <span>{t('projectDescription')}</span>
              <textarea className="input" rows={2} value={draft.description} onChange={(event) => updateProjectField('description', event.target.value)} />
            </label>
            {([
              ['problem', 'problem'],
              ['solution', 'solution'],
              ['target_market', 'targetMarket'],
              ['value_proposition', 'valueProposition'],
              ['business_model', 'businessModel'],
              ['next_steps', 'nextSteps'],
            ] as const).map(([field, label]) => (
              <label key={field} style={{ display: 'grid', gap: 6, fontSize: 13 }}>
                <span>{t(label)}</span>
                <textarea className="input" rows={2} value={draft[field]} onChange={(event) => updateProjectField(field, event.target.value)} />
              </label>
            ))}
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button className="btn btn-primary" type="submit" disabled={savingProject}>
                {savingProject ? t('savingProject') : activeProject ? t('saveProject') : t('createProject')}
              </button>
            </div>
          </form>

          {activeProject && (
            <section className="card" style={{ padding: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
                <Target size={18} color="var(--brand)" />
                <h2 style={{ fontSize: 18, margin: 0 }}>{t('milestones')}</h2>
              </div>
              {activeProject.milestones.length === 0 && <p style={{ color: 'var(--text-muted)' }}>{t('noMilestones')}</p>}
              <div style={{ display: 'grid', gap: 10, marginBottom: 18 }}>
                {activeProject.milestones.map((milestone) => (
                  <div key={milestone.id} className="card" style={{ padding: 12, display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
                    <div>
                      <strong>{milestone.title}</strong>
                      {milestone.details && <p style={{ margin: '4px 0 0', color: 'var(--text-muted)', fontSize: 13 }}>{milestone.details}</p>}
                      {milestone.due_date && <p style={{ margin: '4px 0 0', color: 'var(--text-muted)', fontSize: 12 }}>{t('dueDate')}: {milestone.due_date}</p>}
                    </div>
                    <select
                      className="input"
                      aria-label={`${milestone.title}: ${t('milestoneStatus')}`}
                      value={milestone.status}
                      disabled={savingMilestoneId === milestone.id}
                      onChange={(event) => void handleMilestoneStatusChange(milestone, event.target.value as StartupMilestoneStatus)}
                      style={{ maxWidth: 160 }}
                    >
                      {MILESTONE_STATUSES.map((status) => <option key={status.value} value={status.value}>{t(status.label)}</option>)}
                    </select>
                  </div>
                ))}
              </div>
              <form onSubmit={handleAddMilestone} style={{ display: 'grid', gap: 10 }}>
                <label style={{ display: 'grid', gap: 6, fontSize: 13 }}>
                  <span>{t('milestoneTitle')}</span>
                  <input className="input" maxLength={160} required value={milestoneDraft.title} onChange={(event) => setMilestoneDraft((current) => ({ ...current, title: event.target.value }))} />
                </label>
                <label style={{ display: 'grid', gap: 6, fontSize: 13 }}>
                  <span>{t('milestoneDetails')}</span>
                  <textarea className="input" rows={2} value={milestoneDraft.details} onChange={(event) => setMilestoneDraft((current) => ({ ...current, details: event.target.value }))} />
                </label>
                <label style={{ display: 'grid', gap: 6, fontSize: 13 }}>
                  <span>{t('dueDate')}</span>
                  <input className="input" type="date" value={milestoneDraft.due_date} onChange={(event) => setMilestoneDraft((current) => ({ ...current, due_date: event.target.value }))} />
                </label>
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button className="btn" type="submit" disabled={savingMilestone}>{savingMilestone ? t('savingProject') : t('addMilestone')}</button>
                </div>
              </form>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
