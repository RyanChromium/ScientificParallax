import { ArrowUpRight, ArrowDown, ArrowRight, Mail, Orbit } from 'lucide-react';
import Observation from './observation';
import { contactEmail } from '@/lib/contact';
import { getCopy, languagePath, type Language } from '@/lib/copy';
const repo = 'https://github.com/RyanChromium/ScientificParallax';

export default function ProjectPage({ language }: { language: Language }) {
  const t = getCopy(language);
  return (
    <div
      className={'site-content language-' + language}
      lang={language === 'en' ? 'en' : 'zh-CN'}
    >
      <a className="skip-link" href="#main">
        {t.skip}
      </a>
      <div className="observatory-shell">
        <header className="site-header page-width">
          <a
            className="identity"
            href={languagePath(language)}
            aria-label={t.home}
          >
            <Orbit size={28} strokeWidth={1.5} />
            <span>
              {t.brand}
              <small>{t.brandSub}</small>
            </span>
          </a>
          <nav aria-label={t.navigation}>
            <a href="#focus">{t.nav[0]}</a>
            <a href="#method">{t.nav[1]}</a>
            <a href="#boundaries">{t.nav[2]}</a>
          </nav>
          <div className="header-actions">
            <nav className="language-switch" aria-label={t.languageNavigation}>
              <a
                href={languagePath('zh')}
                hrefLang="zh-CN"
                lang="zh-CN"
                aria-current={language === 'zh' ? 'page' : undefined}
              >
                中文
              </a>
              <a
                href={languagePath('en')}
                hrefLang="en"
                lang="en"
                aria-current={language === 'en' ? 'page' : undefined}
              >
                EN
              </a>
            </nav>
            <a
              className="archive-link"
              href={repo}
              target="_blank"
              rel="noreferrer"
            >
              {t.archive} <ArrowUpRight size={15} />
            </a>
          </div>
        </header>
      </div>
      <main id="main">
        <section className="opening page-width" aria-labelledby="project-title">
          <div className="opening-copy">
            <p className="project-kind">{t.kind}</p>
            <div className="display-title" aria-hidden="true">
              Scientific
              <br />
              <span>
                Parallax<span className="title-period">.</span>
              </span>
            </div>
            <h1 id="project-title">
              <span className="visually-hidden">{t.title}: </span>
              {t.headline[0]}
              <br />
              {t.headline[1]}
            </h1>
            <p className="opening-description multiline">{t.intro}</p>
            <a href="#focus" className="reading-link">
              {t.start} <ArrowDown size={17} />
            </a>
          </div>
          <Observation copy={t.observation} />
          <div className="opening-footnote">
            <span>
              {t.world}
              <strong>{t.perspectives}</strong>
            </span>
            <a href="#premise" aria-label={t.readPremise}>
              <ArrowDown size={20} />
            </a>
          </div>
        </section>
        <section className="premise page-width" id="premise">
          <p className="section-label">{t.premiseLabel}</p>
          <div>
            <h2>
              {t.premiseTitle[0]}
              <br />
              <span>{t.premiseTitle[1]}</span>
            </h2>
            <div className="premise-prose">
              {t.premise.map((p) => (
                <p key={p}>{p}</p>
              ))}
            </div>
          </div>
        </section>
        <section className="focus-section page-width" id="focus">
          <div className="focus-heading">
            <p className="section-label">{t.focusLabel}</p>
            <p className="multiline">{t.focusIntro}</p>
          </div>
          <div className="focus-rows">
            {t.interests.map((item) => (
              <article className="focus-row" key={item.word}>
                <div className="focus-name">
                  <span>{item.tag}</span>
                  <h3>{item.word}</h3>
                </div>
                <div className="focus-body">
                  <h4>{item.title}</h4>
                  <p>{item.body}</p>
                  <p className="focus-limit">{item.limit}</p>
                </div>
              </article>
            ))}
          </div>
        </section>
        <section className="method-section" id="method">
          <div className="page-width">
            <div className="method-intro">
              <p className="section-label">{t.methodLabel}</p>
              <h2>
                {t.methodTitle[0]}
                <br />
                {t.methodTitle[1]}
              </h2>
              <p className="multiline">{t.methodIntro}</p>
            </div>
            <ol className="evidence-loop">
              {t.steps.map(([title, body], i) => (
                <li key={title}>
                  <div className="step-top">
                    <span>{i + 1}</span>
                    {i < 3 && <ArrowRight size={21} />}
                  </div>
                  <h3>{title}</h3>
                  <p>{body}</p>
                </li>
              ))}
            </ol>
            <div className="method-limit">
              <span>{t.pending}</span>
              <p>{t.methodLimit}</p>
            </div>
          </div>
        </section>
        <section className="boundaries page-width" id="boundaries">
          <div className="boundary-intro">
            <p className="section-label">{t.boundaryLabel}</p>
            <h2>
              {t.boundaryTitle[0]}
              <br />
              {t.boundaryTitle[1]}
            </h2>
            <p className="multiline">{t.boundaryIntro}</p>
            <a
              href={repo + '#当前状态'}
              target="_blank"
              rel="noreferrer"
              className="reading-link"
            >
              {t.audit} <ArrowUpRight size={16} />
            </a>
          </div>
          <div className="boundary-list">
            {t.boundaries.map((item) => (
              <article key={item.tag}>
                <span className="boundary-tag">{item.tag}</span>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        </section>
        <footer className="site-footer">
          <div className="page-width">
            <div className="footer-invitation">
              <div>
                <p className="section-label">{t.invitationLabel}</p>
                <h2>
                  {t.invitationTitle[0]}
                  <br />
                  {t.invitationTitle[1]}
                </h2>
              </div>
              <div>
                <p className="multiline">{t.invitation}</p>
                <div className="contact-actions">
                  <a
                    href={`mailto:${contactEmail}`}
                    className="conversation-link email-link"
                    aria-label={t.email}
                  >
                    <Mail size={18} aria-hidden="true" />
                    <span>{t.email}</span>
                  </a>
                  <a
                    href={repo + '/issues'}
                    target="_blank"
                    rel="noreferrer"
                    className="conversation-link"
                  >
                    {t.discuss} <ArrowUpRight size={21} />
                  </a>
                </div>
              </div>
            </div>
            <div className="footer-baseline">
              <a href="#" className="footer-brand">
                Scientific Parallax.
              </a>
              <span>{t.footer}</span>
              <a href={repo} target="_blank" rel="noreferrer">
                GitHub <ArrowUpRight size={14} />
              </a>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}
