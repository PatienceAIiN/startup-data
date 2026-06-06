import { Component, OnInit, signal, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';

const STORAGE_KEY = 'dpdp_consent_v1';

@Component({
  selector: 'app-consent-banner',
  standalone: true,
  encapsulation: ViewEncapsulation.None,
  imports: [CommonModule],
  template: `
    @if (noticeOpen()) {
      <div class="dpdp-modal-backdrop" (click)="closeNotice()" aria-hidden="true"></div>
      <div class="dpdp-modal" role="dialog" aria-modal="true" aria-labelledby="dpdpNoticeTitle">
        <div class="dpdp-modal-head">
          <div class="dpdp-modal-head-icon">
            <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
              <path fill="currentColor" d="M12 2 4 5v6.1c0 5 3.4 9.6 8 10.9 4.6-1.3 8-5.9 8-10.9V5l-8-3Zm-1 14-4-4 1.4-1.4L11 13.2l4.6-4.6L17 10l-6 6Z"/>
            </svg>
          </div>
          <h2 id="dpdpNoticeTitle">Privacy & Data Use Notice</h2>
          <button class="dpdp-modal-close" (click)="closeNotice()" aria-label="Close">×</button>
        </div>
        <div class="dpdp-modal-body">
          <p class="dpdp-modal-lead">
            We're committed to handling your information responsibly and in compliance with India's
            <strong>Digital Personal Data Protection Act, 2023 (DPDP Act)</strong>.
            This notice explains what we collect, why, and the choices available to you.
          </p>

          <h3>1. Who we are (the Data Fiduciary)</h3>
          <p>
            This B2B intelligence directory is operated by <strong>Patience AI</strong>.
            For any privacy queries you can reach our team at
            <a href="mailto:privacy&#64;patienceai.in">privacy&#64;patienceai.in</a>.
          </p>

          <h3>2. What we collect</h3>
          <ul>
            <li><strong>Account data</strong> — email, name, and password hash you provide at signup.</li>
            <li><strong>Usage data</strong> — search queries, filter selections, and items you view, used to improve the directory.</li>
            <li><strong>Technical data</strong> — IP address, browser fingerprint and a small set of cookies for session and preference storage.</li>
            <li><strong>Business directory data</strong> — publicly available company and startup information sourced from
              Zauba Corp, data.gov.in, the Ministry of Corporate Affairs and Startup India, plus contact info we extract
              from a company's own publicly accessible website.</li>
          </ul>

          <h3>3. Why we process it</h3>
          <ul>
            <li>To authenticate you and keep your session secure.</li>
            <li>To deliver search results, exports, and contact lookups you've explicitly requested.</li>
            <li>To improve the platform — diagnostics, debugging, fraud and abuse prevention.</li>
            <li>To meet legal and regulatory obligations under Indian law.</li>
          </ul>

          <h3>4. Your DPDP rights</h3>
          <p>Under the DPDP Act you have the right to:</p>
          <ul>
            <li>Access a summary of personal data we hold about you.</li>
            <li>Correct or update inaccurate personal data.</li>
            <li>Erasure of personal data when the purpose is complete (subject to legal retention).</li>
            <li>Withdraw consent at any time — this won't affect prior lawful processing.</li>
            <li>Nominate another individual to exercise these rights in case of incapacity.</li>
            <li>Raise grievances with our team and, if unresolved, with the Data Protection Board of India.</li>
          </ul>

          <h3>5. Cookies & similar tech</h3>
          <p>
            We use essential cookies to keep you signed in and remember your filter preferences. With your consent,
            we also use analytics cookies to understand how the directory is used so we can improve it.
            <em>Rejecting non-essential</em> disables analytics; the directory itself continues to work.
          </p>

          <h3>6. Sharing & transfers</h3>
          <p>
            We do not sell your personal data. We use Cloudflare R2 for export storage and Neon for our database;
            both are bound by data-processing agreements. Cross-border transfers happen only where permitted by Indian law.
          </p>

          <h3>7. Retention</h3>
          <p>
            Account data is retained while your account is active. Search history is kept for 90 days for diagnostics.
            Public-source directory data may be retained indefinitely as part of the corporate directory.
          </p>

          <h3>8. Security</h3>
          <p>
            We protect your data with TLS in transit, bcrypt password hashing, and rotated JWT-based sessions.
            We're a small team — if you spot anything you'd like to flag, please write to us.
          </p>

          <h3>9. Changes</h3>
          <p>
            We'll surface this banner again whenever the notice changes in a way that materially affects your consent.
          </p>

          <p class="dpdp-modal-foot-note">
            By choosing <strong>Accept all</strong> you consent to the processing described above.
            <strong>Reject non-essential</strong> turns off analytics cookies. You can change your mind anytime by
            clearing site data in your browser.
          </p>
        </div>
        <div class="dpdp-modal-actions">
          <button class="dpdp-btn dpdp-accept" (click)="closeNotice()">OK, got it</button>
        </div>
      </div>
    }
    @if (visible()) {
      <div class="dpdp-banner" role="dialog" aria-live="polite" aria-label="Data privacy notice">
        <div class="dpdp-inner">
          <div class="dpdp-icon">
            <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
              <path fill="currentColor" d="M12 2 4 5v6.1c0 5 3.4 9.6 8 10.9 4.6-1.3 8-5.9 8-10.9V5l-8-3Zm-1 14-4-4 1.4-1.4L11 13.2l4.6-4.6L17 10l-6 6Z"/>
            </svg>
          </div>
          <div class="dpdp-body">
            <strong class="dpdp-title">Your privacy, your choice</strong>
            <p class="dpdp-text">
              We use cookies and process personal data to keep this directory working, remember your preferences, and improve search.
              You're in control — review our notice and choose what you're comfortable with. In line with India's
              <strong>Digital Personal Data Protection Act, 2023</strong>.
            </p>
            <button type="button" class="dpdp-link" (click)="openNotice()">Read full privacy notice</button>
          </div>
          <div class="dpdp-actions">
            <button class="dpdp-btn dpdp-reject" (click)="decide('rejected')">Reject non-essential</button>
            <button class="dpdp-btn dpdp-accept" (click)="decide('accepted')">Accept all</button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    .dpdp-banner {
      position: fixed; left: 16px; right: 16px; bottom: 16px;
      z-index: 2000;
      background: var(--surface, #ffffff);
      color: var(--text-primary, #0f172a);
      border-radius: 16px;
      box-shadow: 0 18px 50px rgba(15,23,42,0.35), 0 0 0 1px rgba(96,165,250,0.25);
      padding: 18px 22px;
      animation: dpdpIn .35s cubic-bezier(.2,.7,.3,1);
      max-width: 1180px; margin: 0 auto;
    }
    @keyframes dpdpIn { from { opacity:0; transform: translateY(20px); } to { opacity:1; transform: translateY(0); } }
    .dpdp-inner {
      display: grid;
      grid-template-columns: 32px 1fr auto;
      gap: 16px;
      align-items: center;
    }
    .dpdp-icon { color: #10b981; display: flex; align-items: center; justify-content: center; }
    .dpdp-title { display: block; font-size: 14px; margin-bottom: 4px; }
    .dpdp-text { margin: 0 0 6px; font-size: 13px; line-height: 1.5; color: var(--text-secondary, #475569); }
    .dpdp-link {
      font-size: 12px; color: #60a5fa; text-decoration: underline; text-underline-offset: 2px;
      background: none; border: 0; padding: 0; cursor: pointer; font-family: inherit;
    }
    .dpdp-link:hover { color: #93c5fd; }
    /* Notice modal */
    .dpdp-modal-backdrop {
      position: fixed; inset: 0; background: rgba(15,23,42,0.6); z-index: 2100;
      animation: dpdpFade .2s ease;
    }
    @keyframes dpdpFade { from { opacity: 0; } to { opacity: 1; } }
    .dpdp-modal {
      position: fixed; z-index: 2101;
      top: 50%; left: 50%; transform: translate(-50%, -50%);
      width: min(720px, 92vw);
      max-height: 85vh; display: flex; flex-direction: column;
      background: var(--surface, #ffffff); color: var(--text-primary, #0f172a);
      border-radius: 14px; overflow: hidden;
      box-shadow: 0 24px 60px rgba(15,23,42,0.45);
      animation: dpdpModalIn .25s cubic-bezier(.2,.7,.3,1);
    }
    @keyframes dpdpModalIn { from { opacity:0; transform: translate(-50%, -45%); } to { opacity:1; transform: translate(-50%, -50%); } }
    .dpdp-modal-head {
      display: flex; align-items: center; gap: 12px;
      padding: 18px 22px;
      border-bottom: 1px solid rgba(148,163,184,0.2);
    }
    .dpdp-modal-head h2 { margin: 0; font-size: 17px; font-weight: 700; flex: 1; }
    .dpdp-modal-head-icon { color: #10b981; }
    .dpdp-modal-close {
      background: transparent; border: 0; font-size: 26px; line-height: 1;
      color: #94a3b8; cursor: pointer; padding: 0 4px;
    }
    .dpdp-modal-close:hover { color: var(--text-primary); }
    .dpdp-modal-body {
      padding: 18px 22px;
      overflow-y: auto;
      font-size: 13.5px; line-height: 1.6;
      color: var(--text-secondary, #475569);
    }
    .dpdp-modal-body h3 {
      font-size: 14px; font-weight: 700; margin: 18px 0 8px;
      color: var(--text-primary, #0f172a);
    }
    .dpdp-modal-body ul { margin: 6px 0 12px 18px; padding: 0; }
    .dpdp-modal-body li { margin-bottom: 4px; }
    .dpdp-modal-body a { color: #60a5fa; }
    .dpdp-modal-lead {
      background: rgba(96,165,250,0.08);
      border: 1px dashed rgba(96,165,250,0.35);
      border-radius: 10px;
      padding: 10px 12px;
      margin-bottom: 12px;
    }
    .dpdp-modal-foot-note {
      margin-top: 16px;
      font-size: 12.5px;
      color: var(--text-muted, #64748b);
    }
    .dpdp-modal-actions {
      padding: 14px 22px;
      border-top: 1px solid rgba(148,163,184,0.2);
      display: flex; justify-content: flex-end;
    }
    .dpdp-actions { display: flex; gap: 8px; flex-shrink: 0; }
    .dpdp-btn {
      border: 1px solid transparent;
      padding: 10px 16px;
      border-radius: 10px;
      font-size: 13px; font-weight: 600;
      cursor: pointer;
      transition: transform .1s ease, background .15s ease;
    }
    .dpdp-btn:hover { transform: translateY(-1px); }
    .dpdp-reject {
      background: transparent;
      border-color: rgba(148,163,184,0.4);
      color: var(--text-primary, #0f172a);
    }
    .dpdp-reject:hover { background: rgba(148,163,184,0.12); }
    .dpdp-accept {
      background: linear-gradient(135deg, #10b981, #059669);
      color: #fff;
    }
    .dpdp-accept:hover { background: linear-gradient(135deg, #059669, #047857); }
    @media (max-width: 720px) {
      .dpdp-inner { grid-template-columns: 1fr; }
      .dpdp-icon { display: none; }
      .dpdp-actions { width: 100%; }
      .dpdp-btn { flex: 1; }
    }
  `],
})
export class ConsentBannerComponent implements OnInit {
  visible = signal(false);
  noticeOpen = signal(false);

  ngOnInit(): void {
    try {
      const v = localStorage.getItem(STORAGE_KEY);
      this.visible.set(!v);
    } catch {
      this.visible.set(true);
    }
  }

  decide(choice: 'accepted' | 'rejected'): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        choice,
        at: new Date().toISOString(),
        version: 1,
      }));
    } catch {}
    this.visible.set(false);
  }

  openNotice(): void { this.noticeOpen.set(true); }
  closeNotice(): void { this.noticeOpen.set(false); }
}
