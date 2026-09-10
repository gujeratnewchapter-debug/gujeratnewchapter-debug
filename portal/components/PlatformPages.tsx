'use client';

import { FormEvent, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Activity, ArrowRight, BarChart3, BookOpen, Building2, CheckCircle2,
  Compass, FileText, Handshake, Lightbulb, LineChart, MapPin, MessageCircle,
  Network, Search, ShieldCheck, Sparkles, Target, Users, WalletCards,
} from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { useI18n } from '@/lib/i18n';
import { createConversation, getPageContent, sendAIMessage, submitServiceRequest } from '@/lib/api';

const copy = {
  en: { eyebrow: 'Ethiopian Startup School', advisor: 'AI Business Advisor', ecosystem: 'Startup Ecosystem', services: 'Business Consultant', analytics: 'Platform intelligence', legal: 'Ethiopian Legal Business', about: 'About Ethiopian Startup School' },
  am: { eyebrow: 'የኢትዮጵያ ስታርትአፕ ትምህርት ቤት', advisor: 'AI የንግድ አማካሪ', ecosystem: 'የስታርትአፕ ሥነ-ምህዳር', services: 'የንግድ አማካሪ', analytics: 'የመድረክ መረጃ', legal: 'የኢትዮጵያ ሕጋዊ ንግድ', about: 'ስለ ኢትዮጵያ ስታርትአፕ ትምህርት ቤት' },
  om: { eyebrow: 'Mana Barnoota Startup Itoophiyaa', advisor: 'Gorsaa Daldalaa AI', ecosystem: 'Sirna Ikosisteemii Startup', services: 'Gorsaa Daldalaa', analytics: 'Odeeffannoo waltajjii', legal: 'Daldala Seera Qabeessa Itoophiyaa', about: 'Waa’ee Mana Barnoota Startup Itoophiyaa' },
  ti: { eyebrow: 'ቤት ትምህርቲ ስታርታፕ ኢትዮጵያ', advisor: 'AI ኣማኻሪ ንግዲ', ecosystem: 'ኢኮሲስተም ስታርታፕ', services: 'ኣማኻሪ ንግዲ', analytics: 'ሓበሬታ መድረኽ', legal: 'ሕጋዊ ንግዲ ኢትዮጵያ', about: 'ብዛዕባ ቤት ትምህርቲ ስታርታፕ ኢትዮጵያ' },
};

function PageIntro({ slug, title, description, icon: Icon }: { slug: string; title: string; description: string; icon: typeof Activity }) {
  const { lang } = useI18n();
  const [page, setPage] = useState<any>(null);
  useEffect(() => { getPageContent(slug).then((response) => setPage(response.data)).catch(() => undefined); }, [slug]);
  const localized = page?.content?.[lang] ?? {};
  const editableTitle = localized.title || page?.title || title;
  const editableDescription = localized.description || page?.description || description;
  return <section className="container platform-page-intro" style={{ paddingTop: 56, paddingBottom: 28 }}>
    <div className="badge" style={{ gap: 7, marginBottom: 14 }}><Sparkles size={13} /> Ethiopian Startup School</div>
    <h1 style={{ maxWidth: 760, marginBottom: 12 }}>{editableTitle}</h1>
    <p className="subtitle" style={{ margin: 0 }}>{editableDescription}</p>
    <Icon size={110} strokeWidth={0.7} color="var(--brand)" className="platform-page-intro-icon" aria-hidden="true" />
  </section>;
}

export function AboutPage() {
  const { lang } = useI18n();
  const text = copy[lang];
  const objectives = ['Make entrepreneurship education practical and accessible', 'Help learners turn problems into validated opportunities', 'Connect founders with trusted ecosystem support', 'Build Ethiopian businesses that create sustainable value'];
  const faqs = [['Who is Ethiopian Startup School for?', 'Learners, founders, innovators, mentors, and organizations building in or for Ethiopia.'], ['Are the courses practical?', 'Yes. Learning is organized around decisions, exercises, experiments, and real venture-building milestones.'], ['Can organizations partner with us?', 'Yes. Partners can support learning, mentorship, research, events, and startup opportunities.']];
  const [page, setPage] = useState<any>(null);
  useEffect(() => { getPageContent('about-us').then((response) => setPage(response.data)).catch(() => undefined); }, []);
  const sections = page?.sections ?? [];
  const section = (key: string, title: string, body: string) => {
    const item = sections.find((candidate: any) => candidate.key === key);
    const localized = item?.content?.[lang] ?? {};
    return { title: localized.title || item?.title || title, body: localized.body || item?.body || body, image: item?.image || null, content: localized.items || item?.content?.items || [] };
  };
  const about = section('about', 'Learn with purpose. Build with context.', 'We bring entrepreneurship education, AI guidance, business consulting, and ecosystem connections into one practical home for Ethiopia.');
  const mission = section('mission', 'Make the next step clearer.', 'Equip Ethiopian learners and founders with relevant knowledge, practical tools, and trusted support to move from ideas to responsible action.');
  const vision = section('vision', 'An Ethiopia where every viable idea can find a path to impact.', 'We envision a connected, skilled, and confident generation of entrepreneurs creating inclusive businesses and solving local problems.');
  const team = section('team', 'People who build alongside you.', 'Educators, operators, technologists, and community builders focused on practical progress.');
  const partners = section('partners', 'Better together.', "We welcome universities, innovation hubs, public institutions, companies, investors, and community organizations that want to strengthen Ethiopia's startup ecosystem.");
  const objectiveSection = section('objectives', 'What we work toward', '',);
  const faqSection = section('faq', 'Frequently Asked Questions', '');
  const teamItems = team.content.length ? team.content : [['Program & learning', 'Curriculum, courses, and learner success'], ['Venture support', 'Business, market, and startup guidance'], ['Technology & AI', 'Tools that make learning and building more useful']];
  const objectiveItems = objectiveSection.content.length ? objectiveSection.content : objectives.map((item) => [item]);
  const faqItems = faqSection.content.length ? faqSection.content : faqs;
  return <><PageIntro slug="about-us" title={text.about} description="A practical learning and venture-building platform for Ethiopia's next generation of founders, innovators, and business leaders." icon={Compass} /><div className="about-page">
    <section id="about" className="about-feature container"><div className="about-image about-image-students" style={about.image ? { backgroundImage: `url(${about.image})` } : undefined} role="img" aria-label="Learners collaborating on a business idea" /><div><span className="about-label">About Ethiopian Startup School</span><h2>{about.title}</h2><p>{about.body}</p></div></section>
    <section className="container section" id="mission"><div className="about-split"><div><span className="about-label">Our Mission</span><h2>{mission.title}</h2><p>{mission.body}</p></div><div className="about-image about-image-mission" style={mission.image ? { backgroundImage: `url(${mission.image})` } : undefined} role="img" aria-label="A founder planning a venture" /></div></section>
    <section className="about-band" id="vision"><div className="container about-band-inner"><div className="about-image about-image-vision" style={vision.image ? { backgroundImage: `url(${vision.image})` } : undefined} role="img" aria-label="Ethiopian innovation and technology" /><div><span className="about-label">Our Vision</span><h2>{vision.title}</h2><p>{vision.body}</p></div></div></section>
    <section className="container section" id="objectives"><span className="about-label">Our Objectives</span><h2>{objectiveSection.title}</h2><div className="about-objectives">{objectiveItems.map((item: any, index: number) => <div className="about-objective" key={item[0]}><strong>0{index + 1}</strong><span>{item[0]}</span></div>)}</div></section>
    <section className="container section" id="team"><div className="about-section-heading"><div><span className="about-label">Our Team</span><h2>{team.title}</h2></div><p className="muted">{team.body}</p></div><div className="about-team-grid">{teamItems.map((item: any, index: number) => <div className="about-person" key={item[0]}><div className={`about-avatar about-avatar-${index + 1}`}><Users size={29} /></div><h3>{item[0]}</h3><p>{item[1]}</p></div>)}</div></section>
    <section className="about-partners" id="partners"><div className="container"><span className="about-label">Partners</span><h2>{partners.title}</h2><p>{partners.body}</p><div className="about-partner-list">{(partners.content.length ? partners.content.map((item: any) => item[0]) : ['Universities', 'Innovation hubs', 'Industry partners', 'Capital partners', 'Public institutions']).map((item: string) => <span key={item}>{item}</span>)}</div></div></section>
    <section className="container section about-contact-faq"><div id="contact" className="about-contact"><span className="about-label">Contact Us</span><h2>Start a conversation.</h2><p>Reach our team through the contact form in the footer for partnerships, learning support, or ecosystem collaboration.</p><Link href="/contact" className="btn btn-primary">Contact the team <ArrowRight size={16} /></Link></div><div id="faq" className="about-faq"><span className="about-label">{faqSection.title}</span>{faqItems.map((item: any) => <details key={item[0]}><summary>{item[0]}</summary><p>{item[1]}</p></details>)}</div></section>
  </div></>;
}

export function AnalyticsPage() {
  const stats = [{ label: 'Website visitors', value: '18,642', delta: '+18.4%', icon: Users }, { label: 'Learners enrolled', value: '3,284', delta: '+12.8%', icon: BookOpen }, { label: 'Published courses', value: '42', delta: '+4 this month', icon: LineChart }, { label: 'Certificates issued', value: '1,126', delta: '+9.6%', icon: ShieldCheck }];
  const visitors = [42, 51, 48, 63, 58, 74, 69, 82, 78, 91, 87, 100];
  return <><PageIntro slug="analytics" title="Platform intelligence" description="A clear view of reach, learning activity, and the startup-support pipeline. Connect these cards to live analytics events when your production tracking endpoint is ready." icon={BarChart3} />
    <section className="container" style={{ paddingBottom: 64 }}><div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 14, marginBottom: 18 }}>{stats.map(({ label, value, delta, icon: Icon }) => <div className="card" key={label} style={{ padding: 18 }}><Icon size={19} color="var(--secondary-teal)" /><p className="muted" style={{ fontSize: 13, margin: '14px 0 2px' }}>{label}</p><strong style={{ fontSize: 27, color: 'var(--primary-navy)' }}>{value}</strong><p style={{ color: 'var(--brand-dark)', fontSize: 12, margin: '4px 0 0' }}>{delta}</p></div>)}</div>
      <div className="card" style={{ padding: 24 }}><div style={{ display: 'flex', justifyContent: 'space-between', gap: 14, alignItems: 'start', flexWrap: 'wrap' }}><div><h2 style={{ margin: 0, fontSize: 22 }}>Visitors over the last 12 months</h2><p className="muted" style={{ margin: '4px 0 0', fontSize: 13 }}>Unique visitors, shown as an illustrative product view.</p></div><span className="badge"><Activity size={13} /> Live-ready</span></div><div style={{ height: 220, display: 'flex', gap: 12, alignItems: 'end', borderBottom: '1px solid var(--border)', padding: '26px 4px 0', marginTop: 22 }}>{visitors.map((height, index) => <div key={index} style={{ flex: 1, height: `${height}%`, minHeight: 18, borderRadius: '6px 6px 0 0', background: index > 8 ? 'var(--secondary-teal)' : 'var(--brand-emerald)', opacity: 0.45 + index / 24, position: 'relative' }} title={`${height}% relative traffic`}><span style={{ position: 'absolute', bottom: -25, left: '50%', transform: 'translateX(-50%)', color: 'var(--text-muted)', fontSize: 11 }}>M{index + 1}</span></div>)}</div></div>
    </section></>;
}

export function AdvisorPage() {
  const { lang } = useI18n();
  const { isAuthenticated } = useAuth();
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [busy, setBusy] = useState(false);
  async function ask(event: FormEvent) { event.preventDefault(); if (!question.trim()) return; setBusy(true); setAnswer(''); const prompt = `Act as an Ethiopia-focused startup advisor. Answer carefully and practically. Do not invent Ethiopian laws, regulations, taxes, licenses, or government procedures. When legal or tax accuracy matters, say what must be verified with the relevant Ethiopian authority or a qualified professional. User question: ${question}`; try { const conversation = await createConversation('coach', 'Ethiopian business advisor'); const result = await sendAIMessage(conversation.data.id, prompt); setAnswer(result.data.content); } catch { setAnswer(isAuthenticated ? 'The advisor is temporarily unavailable. Please verify legal and tax questions with an official Ethiopian authority or qualified professional.' : 'Sign in to connect to the advisor. For now, start with a specific question about your customer, market, business model, MVP, or funding plan.'); } finally { setBusy(false); } }
  const tools = ['Business idea analysis', 'Market gaps and customer needs', 'Competitor and SWOT analysis', 'Business model and MVP planning', 'Valuation, funding, and pitch preparation', 'Marketing and growth planning'];
  return <><PageIntro slug="ai-business-advisor" title="Ethiopia-focused AI Business Advisor" description="Turn a business question into a practical next step. The advisor is designed to distinguish general guidance from legal or tax matters that require official verification." icon={MessageCircle} />
    <section className="container" style={{ paddingBottom: 64, display: 'grid', gridTemplateColumns: 'minmax(0, 1.25fr) minmax(240px, .75fr)', gap: 20 }}><div className="card" style={{ padding: 24 }}><div className="badge" style={{ marginBottom: 16 }}><MessageCircle size={13} /> Advisor workspace</div><form onSubmit={ask}><label className="label" htmlFor="advisor-question">What are you working through?</label><textarea id="advisor-question" className="input" rows={6} value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Example: How can I validate a logistics problem for small businesses in Addis Ababa?" /><button className="btn btn-primary" type="submit" disabled={busy} style={{ marginTop: 14 }}>{busy ? 'Thinking...' : 'Ask the advisor'} <ArrowRight size={16} /></button></form>{answer && <div style={{ marginTop: 22, padding: 18, background: 'var(--soft-green)', borderLeft: '4px solid var(--brand)', whiteSpace: 'pre-wrap' }}>{answer}</div>}</div><aside className="feature-card"><h2 style={{ fontSize: 20, marginTop: 0 }}>Explore a tool</h2>{tools.map((tool) => <div key={tool} style={{ display: 'flex', gap: 9, alignItems: 'start', padding: '11px 0', borderBottom: '1px solid var(--border)', fontSize: 14 }}><CheckCircle2 size={16} color="var(--brand-dark)" />{tool}</div>)}<p className="muted" style={{ fontSize: 12, marginBottom: 0 }}>Legal and tax answers should always be checked against current official sources.</p></aside></section></>;
}

const services = ['Start a Business', 'Market Research', 'MVP Builder', 'Business Valuation', 'Business Plan', 'Pitch Deck', 'Startup Strategy', 'Legal Business Guidance', 'Mentor Matching'];
export function ServicesPage() {
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);
  async function request(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setBusy(true); const form = event.currentTarget; const data = new FormData(form); try { await submitServiceRequest({ service: String(data.get('service') || ''), notes: String(data.get('notes') || '') }); setSubmitted(true); form.reset(); } catch { setSubmitted(false); } finally { setBusy(false); } }
  return <><PageIntro slug="business-consultant" title="Business Consultant" description="Request focused help from the Ethiopian Startup School network, from market research and MVP planning to valuation, strategy, and mentor matching." icon={Handshake} />
    <section className="container services-consultant-layout" style={{ paddingBottom: 64, display: 'grid', gridTemplateColumns: 'minmax(0, .9fr) minmax(280px, 1.1fr)', gap: 20 }}><div><h2 style={{ fontSize: 22 }}>Choose a service</h2><div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>{services.map((service) => <div className="feature-card" key={service} style={{ padding: 16 }}><Target size={18} color="var(--brand)" /><p style={{ margin: '10px 0 0', fontWeight: 600, fontSize: 14 }}>{service}</p></div>)}</div></div><form className="card" onSubmit={request} style={{ padding: 24 }}><h2 style={{ fontSize: 22, marginTop: 0 }}>Request support</h2><label className="label" htmlFor="service">Service</label><select className="input" id="service" name="service" defaultValue={services[0]}>{services.map((service) => <option key={service}>{service}</option>)}</select><label className="label" htmlFor="service-notes" style={{ marginTop: 14 }}>What do you need?</label><textarea className="input" id="service-notes" name="notes" rows={5} required placeholder="Tell us about your stage, goal, timeline, and location." /><button className="btn btn-primary" type="submit" disabled={busy} style={{ marginTop: 14 }}>{busy ? 'Sending...' : 'Send request'} <ArrowRight size={16} /></button>{submitted && <p style={{ color: 'var(--brand-dark)', fontSize: 13, marginBottom: 0 }}>Request received. The platform team can now review and assign it to a service provider.</p>}</form></section></>;
}

const defaultEcosystem = [{ name: 'Startups', count: '1,240', detail: 'Discover ventures by sector, stage, and location.', icon: RocketIcon }, { name: 'Investors', count: '86', detail: 'Connect capital providers with investable ventures.', icon: WalletCards }, { name: 'Mentors', count: '214', detail: 'Find operators and experts ready to share experience.', icon: Users }, { name: 'Incubators & accelerators', count: '38', detail: 'Compare programs, cohorts, and application windows.', icon: Building2 }, { name: 'Innovation hubs', count: '52', detail: 'Explore communities, labs, and collaboration spaces.', icon: Network }, { name: 'Universities & stakeholders', count: '67', detail: 'Build bridges across research, talent, and public support.', icon: MapPin }];
function RocketIcon(props: { size?: number; color?: string }) { return <Sparkles {...props} />; }
export function EcosystemPage() {
  const { lang } = useI18n();
  const [query, setQuery] = useState('');
  const [page, setPage] = useState<any>(null);

  useEffect(() => {
    getPageContent('startup-ecosystem').then((response) => setPage(response.data)).catch(() => undefined);
  }, []);

  const localized = page?.content?.[lang] ?? {};
  const sections = page?.sections ?? [];
  const sectionItems = (key: string) => {
    const section = sections.find((item: any) => item.key === key);
    const content = section?.content?.[lang] ?? section?.content ?? {};
    return content.items ?? section?.content?.items ?? [];
  };
  const configuredCards = sectionItems('categories');
  const ecosystem = (configuredCards.length ? configuredCards : defaultEcosystem).map((item: any, index: number) => {
    const values = Array.isArray(item) ? { name: item[0], count: item[1], detail: item[2] } : item;
    return { ...values, icon: defaultEcosystem[index % defaultEcosystem.length].icon };
  });
  const summary = sectionItems('summary');
  const summaryItems = (summary.length ? summary : [
    ['Companies', '1,240', '+12% this year'],
    ['Funding rounds', '88', 'Tracked across Ethiopia'],
    ['Startup employees', '15.4k', 'Estimated ecosystem jobs'],
    ['Organizations', '417', 'Programs and partners'],
  ]).map((item: any) => Array.isArray(item) ? { label: item[0], value: item[1], detail: item[2] } : { label: item.label, value: item.value, detail: item.detail });
  const visible = ecosystem.filter((item: any) => `${item.name} ${item.detail}`.toLowerCase().includes(query.toLowerCase()));
  const dashboardTitle = localized.dashboard_title || sections.find((item: any) => item.key === 'dashboard')?.title || 'Explore the market';
  const dashboardKicker = localized.dashboard_kicker || sections.find((item: any) => item.key === 'dashboard')?.body || 'Ecosystem overview';
  return <><PageIntro slug="startup-ecosystem" title="Ethiopia's startup ecosystem" description="Explore the companies, capital, talent, programs, hubs, universities, and institutions shaping Ethiopia's innovation economy." icon={Network} /><section className="ecosystem-dashboard"><div className="ecosystem-dashboard-inner"><div className="ecosystem-toolbar"><div><p className="ecosystem-kicker">{dashboardKicker}</p><h2>{dashboardTitle}</h2></div><label className="ecosystem-search"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={localized.search_placeholder || 'Search companies, investors, sectors...'} /></label></div><div className="ecosystem-summary">{summaryItems.map((item: any) => <div key={item.label}><span>{item.label}</span><strong>{item.value}</strong><small>{item.detail}</small></div>)}</div><div className="ecosystem-dashboard-grid">{visible.map(({ name, count, detail, icon: Icon }: any) => <article className="ecosystem-data-card" key={name}><div className="ecosystem-card-icon"><Icon size={19} /></div><div className="ecosystem-card-heading"><h3>{name}</h3><strong>{count}</strong></div><p>{detail}</p><div className="ecosystem-card-meta"><span>Data category</span><span>Updated monthly</span></div></article>)}</div>{visible.length === 0 && <p className="muted" style={{ padding: 24 }}>No ecosystem category matches “{query}”.</p>}</div></section></>;
}

export function LegalBusinessCoursePage() { const modules = ['Choose a suitable business structure', 'Establish and register the business', 'Obtain sector and municipal licenses', 'Complete tax registration and records', 'Operate, renew, and stay compliant']; return <><PageIntro slug="ethiopian-legal-business" title="Ethiopian Legal Business" description="A practical course map for starting, registering, and operating a business in Ethiopia, with source links to verify current procedures." icon={FileText} /><section className="container" style={{ paddingBottom: 64, display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(240px, .8fr)', gap: 20 }}><div className="card" style={{ padding: 24 }}><div className="badge"><BookOpen size={13} /> Course outline</div><h2 style={{ fontSize: 23, margin: '14px 0' }}>From idea to compliant operation</h2>{modules.map((module, index) => <div key={module} style={{ display: 'flex', gap: 14, padding: '16px 0', borderBottom: '1px solid var(--border)' }}><strong style={{ color: 'var(--brand-dark)', minWidth: 28 }}>0{index + 1}</strong><div><strong>{module}</strong><p className="muted" style={{ margin: '4px 0 0', fontSize: 13 }}>Step-by-step learning activity with checklists, decisions, and verification points.</p></div></div>)}</div><aside className="feature-card"><h2 style={{ fontSize: 20, marginTop: 0 }}>Official starting points</h2><p className="muted" style={{ fontSize: 13 }}>Always confirm the latest requirements, fees, forms, and responsible office before acting.</p>{[['Ethiopian Investment Commission', 'https://investethiopia.gov.et/'], ['Ministry of Trade and Regional Integration', 'https://motri.gov.et/'], ['Ethiopian Revenues Ministry', 'https://www.mor.gov.et/'], ['Federal Negarit Gazette', 'https://www.fsc.gov.et/']].map(([name, url]) => <a href={url} target="_blank" rel="noreferrer" key={url} style={{ display: 'block', padding: '11px 0', borderBottom: '1px solid var(--border)', color: 'var(--secondary-teal)', fontSize: 13, fontWeight: 600 }}>{name} <ArrowRight size={13} style={{ display: 'inline' }} /></a>)}<p style={{ fontSize: 12, marginBottom: 0, marginTop: 18 }}><strong>Educational disclaimer:</strong> This course is educational information, not legal or tax advice. Consult a qualified Ethiopian professional for your situation.</p></aside></section></>; }