import { Component, Inject, OnInit, ViewEncapsulation, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { environment } from '../../../../environments/environment';
import { EnrichmentBusService } from '../../../core/services/enrichment-bus.service';
import { MatSnackBar } from '@angular/material/snack-bar';

export interface StartupDetail {
  id: string;
  profile_id: string;
  profile_url: string | null;
  company_name: string;
  description: string | null;
  industry: string | null;
  sector: string | null;
  stage: string | null;
  state: string | null;
  city: string | null;
  website: string | null;
  logo_url: string | null;
  badges: string[];
  dpiit_recognised: boolean;
  contact_email: string | null;
  contact_phone: string | null;
  contact_address: string | null;
  linkedin_url: string | null;
  twitter_url: string | null;
  facebook_url: string | null;
  source_url: string | null;
  cin_real: string | null;
  gst: string | null;
  contact_enriched_at: string | null;
  scraped_at: string | null;
  dipp_number?: string | null;
  extras?: Record<string, any>;
}

export interface StartupDetailDialogData {
  cin: string | null;
  companyName: string;
  fallback?: {
    state?: string | null;
    company_status?: string | null;
    company_category?: string | null;
    date_of_incorporation?: string | null;
    website?: string | null;
    match_method?: string | null;
  };
}

@Component({
  selector: 'app-startup-detail-dialog',
  standalone: true,
  encapsulation: ViewEncapsulation.None,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule, MatProgressBarModule],
  template: `
    <div class="sd-dialog">
      @if (loading()) {
        <mat-progress-bar mode="indeterminate"></mat-progress-bar>
      }

      <div class="sd-header">
        <div class="sd-header-main">
          <div class="sd-logo">
            @if (s()?.logo_url) {
              <img [src]="s()!.logo_url" alt="logo" />
            } @else {
              <mat-icon>rocket_launch</mat-icon>
            }
          </div>
          <div>
            <h2>{{ s()?.company_name || data.companyName }}</h2>
            <div class="sd-badges">
              <span class="badge badge-startup">🚀 Startup</span>
              @if (s()?.dpiit_recognised) {
                <span class="badge badge-dpiit">✓ DPIIT Recognised</span>
              }
              @for (b of s()?.badges || []; track b) {
                <span class="badge badge-soft">{{ b }}</span>
              }
            </div>
          </div>
        </div>
        <button mat-icon-button (click)="close()" aria-label="Close">
          <mat-icon>close</mat-icon>
        </button>
      </div>

      @if (s(); as v) {
        <div class="sd-tip">
          <mat-icon class="sd-tip-icon">tips_and_updates</mat-icon>
          <span>Details still loading? Close this and tap again in a moment — we're gathering fresh info from the company's site.</span>
        </div>
        @if (v.description) {
          <div class="sd-desc">{{ v.description }}</div>
        }

        <div class="sd-grid">
          @if (v.stage) {
            <div class="sd-tile">
              <div class="sd-tile-icon">🌱</div>
              <div>
                <div class="sd-label">STAGE</div>
                <div class="sd-val">{{ v.stage }}</div>
              </div>
            </div>
          }
          @if (v.industry) {
            <div class="sd-tile">
              <div class="sd-tile-icon">⚡</div>
              <div>
                <div class="sd-label">FOCUS INDUSTRY</div>
                <div class="sd-val">{{ v.industry }}</div>
              </div>
            </div>
          }
          @if (v.sector) {
            <div class="sd-tile">
              <div class="sd-tile-icon">📈</div>
              <div>
                <div class="sd-label">FOCUS SECTOR</div>
                <div class="sd-val">{{ v.sector }}</div>
              </div>
            </div>
          }
          @if (formatLocation(v) !== '—') {
            <div class="sd-tile">
              <div class="sd-tile-icon">📍</div>
              <div>
                <div class="sd-label">LOCATION</div>
                <div class="sd-val">{{ formatLocation(v) }}</div>
              </div>
            </div>
          }
          @if (v.scraped_at) {
            <div class="sd-tile">
              <div class="sd-tile-icon">📅</div>
              <div>
                <div class="sd-label">INDEXED ON</div>
                <div class="sd-val">{{ v.scraped_at | date:'mediumDate':'+0530' }}</div>
              </div>
            </div>
          }
          @if (v.dpiit_recognised) {
            <div class="sd-tile">
              <div class="sd-tile-icon">✓</div>
              <div>
                <div class="sd-label">DPIIT RECOGNISED</div>
                <div class="sd-val">{{ v.dipp_number || 'Yes' }}</div>
              </div>
            </div>
          }
          @if (v.cin_real) {
            <div class="sd-tile">
              <div class="sd-tile-icon">#</div>
              <div>
                <div class="sd-label">CIN</div>
                <div class="sd-val">{{ v.cin_real }}</div>
              </div>
            </div>
          }
          @if (v.gst) {
            <div class="sd-tile">
              <div class="sd-tile-icon">🧾</div>
              <div>
                <div class="sd-label">GST</div>
                <div class="sd-val">{{ v.gst }}</div>
              </div>
            </div>
          }
          @if (v.extras?.['founded']) {
            <div class="sd-tile">
              <div class="sd-tile-icon">📅</div>
              <div>
                <div class="sd-label">FOUNDED</div>
                <div class="sd-val">{{ v.extras!['founded'] }}</div>
              </div>
            </div>
          }
          @if (v.extras?.['headquarters']) {
            <div class="sd-tile">
              <div class="sd-tile-icon">🏢</div>
              <div>
                <div class="sd-label">HEADQUARTERS</div>
                <div class="sd-val">{{ v.extras!['headquarters'] }}</div>
              </div>
            </div>
          }
          @if (v.extras?.['founders']) {
            <div class="sd-tile">
              <div class="sd-tile-icon">👤</div>
              <div>
                <div class="sd-label">FOUNDER(S)</div>
                <div class="sd-val">{{ v.extras!['founders'] }}</div>
              </div>
            </div>
          }
          @if (v.extras?.['ceo']) {
            <div class="sd-tile">
              <div class="sd-tile-icon">🎖️</div>
              <div>
                <div class="sd-label">CEO</div>
                <div class="sd-val">{{ v.extras!['ceo'] }}</div>
              </div>
            </div>
          }
          @if (v.extras?.['employees']) {
            <div class="sd-tile">
              <div class="sd-tile-icon">👥</div>
              <div>
                <div class="sd-label">EMPLOYEES</div>
                <div class="sd-val">{{ v.extras!['employees'] }}</div>
              </div>
            </div>
          }
          @if (v.extras?.['revenue']) {
            <div class="sd-tile">
              <div class="sd-tile-icon">💰</div>
              <div>
                <div class="sd-label">REVENUE</div>
                <div class="sd-val">{{ v.extras!['revenue'] }}</div>
              </div>
            </div>
          }
          @if (v.extras?.['parent']) {
            <div class="sd-tile">
              <div class="sd-tile-icon">🌐</div>
              <div>
                <div class="sd-label">PARENT</div>
                <div class="sd-val">{{ v.extras!['parent'] }}</div>
              </div>
            </div>
          }
          @if (v.extras?.['type']) {
            <div class="sd-tile">
              <div class="sd-tile-icon">🏷️</div>
              <div>
                <div class="sd-label">TYPE</div>
                <div class="sd-val">{{ v.extras!['type'] }}</div>
              </div>
            </div>
          }
        </div>
        @if (v.extras?.['google_ai_overview']) {
          <div class="sd-ai-card">
            <div class="sd-ai-head">
              <span class="sd-ai-spark">✦</span>
              <span>Google AI Overview</span>
            </div>
            <div class="sd-ai-body">
              @for (b of parseAiOverview(v.extras!['google_ai_overview']); track $index) {
                @if (b.type === 'heading') {
                  <h4 class="sd-ai-h">{{ b.text }}</h4>
                } @else if (b.type === 'list') {
                  <ul class="sd-ai-list">
                    @for (it of b.items; track $index) {
                      <li>
                        @if (it.title) {
                          <strong>{{ it.title }}:</strong>
                        }
                        <span>{{ it.text }}</span>
                      </li>
                    }
                  </ul>
                } @else {
                  <p class="sd-ai-p">{{ b.text }}</p>
                }
              }
            </div>
          </div>
        }
        @if (v.extras?.['snippet'] && !v.extras?.['google_ai_overview']) {
          <div class="sd-snippet">
            <div class="sd-snippet-head">From the web</div>
            <p>{{ v.extras!['snippet'] }}</p>
            @if (v.extras?.['wikipedia']) {
              <a [href]="v.extras!['wikipedia']" target="_blank" rel="noopener" class="sd-link">Wikipedia</a>
            }
          </div>
        }

        @if (dynamicExtras(v).length || enriching()) {
          <div class="sd-contact">
            <div class="sd-contact-head">
              <mat-icon>insights</mat-icon>
              <span>Financial &amp; corporate details</span>
              @if (enriching()) {
                <span class="sd-enriching">fetching financial info…</span>
              }
            </div>
            <div class="sd-contact-grid">
              @for (kv of dynamicExtras(v); track kv.key) {
                <div>
                  <div class="sd-label">{{ kv.label }}</div>
                  <div class="sd-val">{{ kv.value }}</div>
                </div>
              }
            </div>
          </div>
        }

        @if (hasAnyContact(v) || enriching()) {
          <div class="sd-contact">
            <div class="sd-contact-head">
              <mat-icon>mail</mat-icon>
              <span>Contact</span>
              @if (enriching()) {
                <span class="sd-enriching">fetching contacts…</span>
              }
            </div>
            <div class="sd-contact-grid">
              @if (v.contact_email) {
                <div>
                  <div class="sd-label">EMAIL</div>
                  <a [href]="'mailto:' + v.contact_email" class="sd-link">{{ v.contact_email }}</a>
                </div>
              }
              @if (v.contact_phone) {
                <div>
                  <div class="sd-label">PHONE</div>
                  <a [href]="'tel:' + v.contact_phone" class="sd-link">{{ v.contact_phone }}</a>
                </div>
              }
              @if (v.website) {
                <div>
                  <div class="sd-label">WEBSITE</div>
                  <a [href]="v.website" target="_blank" rel="noopener" class="sd-link">{{ v.website }}</a>
                </div>
              }
              @if (v.linkedin_url) {
                <div>
                  <div class="sd-label">LINKEDIN</div>
                  <a [href]="v.linkedin_url" target="_blank" rel="noopener" class="sd-link">Profile</a>
                </div>
              }
              @if (v.twitter_url) {
                <div>
                  <div class="sd-label">TWITTER / X</div>
                  <a [href]="v.twitter_url" target="_blank" rel="noopener" class="sd-link">Profile</a>
                </div>
              }
              @if (v.facebook_url) {
                <div>
                  <div class="sd-label">FACEBOOK</div>
                  <a [href]="v.facebook_url" target="_blank" rel="noopener" class="sd-link">Page</a>
                </div>
              }
              @if (v.contact_address) {
                <div class="sd-contact-wide">
                  <div class="sd-label">ADDRESS</div>
                  <div class="sd-val">{{ v.contact_address }}</div>
                </div>
              }
            </div>
          </div>
        }

        @if (!enriching() && enrichAttempted() && !hasAnyContact(v) && !dynamicExtras(v).length) {
          <div class="sd-empty">
            <mat-icon>search_off</mat-icon>
            <div>
              <div class="sd-empty-title">No verified data found yet</div>
              <div class="sd-empty-sub">We could not confirm contact or financial details for this entity right now. Try again in a few minutes — sources may surface new info.</div>
            </div>
          </div>
        }

        <div class="sd-actions">
          <button mat-stroked-button color="primary" (click)="copyDetails()">
            <mat-icon>content_copy</mat-icon>
            Copy Details
          </button>
          <div style="flex: 1"></div>
          <button mat-stroked-button color="primary" (click)="exportSingle('csv')" [disabled]="exporting()">
            <mat-icon>description</mat-icon>
            Export CSV
          </button>
          <button mat-stroked-button color="primary" (click)="exportSingle('xlsx')" [disabled]="exporting()">
            <mat-icon>grid_on</mat-icon>
            Export Excel
          </button>
          @if (v.website) {
            <a mat-flat-button color="accent" [href]="v.website" target="_blank" rel="noopener">
              <mat-icon>language</mat-icon>
              Visit Website
            </a>
          }
          <button mat-flat-button color="primary" (click)="close()">Close</button>
        </div>
      } @else if (!loading() && error()) {
        <div class="sd-error">{{ error() }}</div>
        <div class="sd-actions"><button mat-flat-button (click)="close()">Close</button></div>
      }
    </div>
  `,
  styles: [`
    .sd-dialog { padding: 0; color: var(--text-primary, #0f172a); background: var(--bg-secondary, #ffffff); }
    /* Force the Material dialog surface to follow our theme tokens so the
       container itself isn't stuck on white in dark mode. */
    .mat-mdc-dialog-surface:has(.sd-dialog) { background: var(--bg-secondary, #ffffff) !important; }
    .sd-header { display: flex; justify-content: space-between; align-items: flex-start; padding: 20px 24px; border-bottom: 1px solid rgba(148,163,184,.25); background: linear-gradient(135deg, rgba(96,165,250,.08), rgba(16,185,129,.06)); }
    .sd-header-main { display: flex; gap: 16px; align-items: center; }
    .sd-logo { width: 56px; height: 56px; border-radius: 12px; background: rgba(96,165,250,.15); display: flex; align-items: center; justify-content: center; overflow: hidden; }
    .sd-logo img { width: 100%; height: 100%; object-fit: cover; }
    .sd-logo mat-icon { font-size: 30px; color: #60a5fa; }
    h2 { margin: 0 0 8px; font-size: 20px; font-weight: 700; line-height: 1.2; }
    .sd-badges { display: flex; gap: 6px; flex-wrap: wrap; }
    .badge { font-size: 11px; padding: 3px 10px; border-radius: 999px; font-weight: 600; }
    .badge-startup { background: rgba(96,165,250,.15); color: #60a5fa; }
    .badge-dpiit { background: rgba(16,185,129,.15); color: #10b981; }
    .badge-soft { background: rgba(148,163,184,.18); color: #64748b; }
    .sd-desc { padding: 16px 24px 0; color: var(--text-secondary, #64748b); font-size: 14px; line-height: 1.5; }
    .sd-grid { padding: 16px 24px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .sd-tile { display: flex; gap: 12px; padding: 14px; border: 1px solid var(--border, rgba(148,163,184,.22)); border-radius: 10px; align-items: flex-start; background: var(--bg-tertiary, rgba(248,250,252,.4)); }
    .sd-tile-icon { font-size: 20px; line-height: 1; padding-top: 2px; }
    .sd-label { font-size: 11px; font-weight: 700; letter-spacing: .04em; color: #64748b; margin-bottom: 4px; }
    .sd-val { font-size: 14px; font-weight: 600; color: var(--text-primary, #0f172a); }
    .sd-actions { display: flex; gap: 10px; justify-content: flex-end; padding: 16px 24px 20px; border-top: 1px solid rgba(148,163,184,.18); }
    .sd-contact { padding: 16px 24px; border-top: 1px solid rgba(148,163,184,.18); }
    .sd-contact-head { display: flex; align-items: center; gap: 6px; font-weight: 700; font-size: 13px; letter-spacing: .04em; color: #10b981; margin-bottom: 12px; }
    .sd-contact-head mat-icon { font-size: 18px; width: 18px; height: 18px; }
    .sd-enriching { margin-left: 8px; font-weight: 500; color: #94a3b8; font-size: 12px; letter-spacing: 0; text-transform: none; }
    .sd-contact-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 24px; }
    .sd-contact-wide { grid-column: 1 / -1; }
    .sd-link { color: #60a5fa; font-size: 14px; word-break: break-all; }
    .sd-link:hover { text-decoration: underline; }
    .sd-snippet {
      margin: 0 24px 12px;
      padding: 12px 14px;
      background: rgba(148,163,184,0.08);
      border-left: 3px solid #60a5fa;
      border-radius: 6px;
      font-size: 13px; line-height: 1.5; color: var(--text-secondary, #475569);
    }
    .sd-snippet-head { font-size: 11px; font-weight: 700; letter-spacing: .06em; color: #60a5fa; margin-bottom: 6px; }
    /* Google AI Overview card */
    .sd-ai-card {
      margin: 0 24px 14px;
      background: linear-gradient(180deg, rgba(168,85,247,0.06), rgba(168,85,247,0.02));
      border: 1px solid rgba(168,85,247,0.25);
      border-radius: 12px;
      overflow: hidden;
    }
    .sd-ai-head {
      display: flex; align-items: center; gap: 8px;
      padding: 10px 14px;
      background: rgba(168,85,247,0.10);
      font-size: 12px; font-weight: 700; letter-spacing: .04em;
      color: #a855f7; text-transform: uppercase;
    }
    .sd-ai-spark { font-size: 14px; }
    .sd-ai-body { padding: 12px 16px 14px; color: var(--text-primary, #0f172a); }
    .sd-ai-h { margin: 10px 0 6px; font-size: 13.5px; font-weight: 700; color: var(--text-primary, #0f172a); }
    .sd-ai-h:first-child { margin-top: 0; }
    .sd-ai-p { margin: 0 0 8px; font-size: 13.5px; line-height: 1.55; color: var(--text-secondary, #475569); }
    .sd-ai-p:last-child { margin-bottom: 0; }
    .sd-ai-list { margin: 4px 0 10px; padding: 0; list-style: none; }
    .sd-ai-list li {
      position: relative;
      padding: 6px 8px 6px 22px;
      margin-bottom: 4px;
      font-size: 13.5px; line-height: 1.5;
      color: var(--text-primary, #0f172a);
      background: var(--bg-tertiary, rgba(248,250,252,.5));
      border-radius: 6px;
      border-left: 2px solid #a855f7;
    }
    .sd-ai-list li::before {
      content: "•";
      position: absolute; left: 8px; top: 6px;
      color: #a855f7; font-weight: 700;
    }
    .sd-ai-list li strong { color: var(--text-primary, #0f172a); margin-right: 4px; font-weight: 700; }
    .sd-ai-list li span { color: var(--text-secondary, #475569); }
    .sd-snippet p { margin: 0 0 6px; }
    .sd-tip {
      display: flex; align-items: center; gap: 8px;
      margin: 12px 24px 0;
      padding: 8px 12px;
      background: rgba(96,165,250,0.08);
      border: 1px dashed rgba(96,165,250,0.35);
      border-radius: 10px;
      font-size: 12.5px;
      color: var(--text-secondary, #475569);
      line-height: 1.45;
    }
    .sd-tip-icon { font-size: 18px; width: 18px; height: 18px; color: #60a5fa; }
    .sd-error { padding: 24px; color: #ef4444; }
    .sd-empty { display: flex; gap: 12px; align-items: flex-start; margin: 0 24px 12px;
      padding: 14px 16px; border: 1px dashed var(--border, rgba(148,163,184,.4));
      border-radius: 10px; background: var(--bg-tertiary, rgba(248,250,252,.4)); }
    .sd-empty mat-icon { color: var(--text-muted, #94a3b8); }
    .sd-empty-title { font-weight: 700; font-size: 14px; color: var(--text-primary, #0f172a); }
    .sd-empty-sub { font-size: 12.5px; color: var(--text-secondary, #475569); margin-top: 4px; }
    @media (max-width: 720px) { .sd-grid { grid-template-columns: 1fr; } }
  `],
})
export class StartupDetailDialogComponent implements OnInit {
  private http = inject(HttpClient);
  private ref = inject(MatDialogRef<StartupDetailDialogComponent>);
  private bus = inject(EnrichmentBusService);
  private snack = inject(MatSnackBar);

  s = signal<StartupDetail | null>(null);
  loading = signal(true);
  enriching = signal(false);
  exporting = signal(false);
  enrichStage = signal<string>('searching the web…');
  enrichAttempted = signal(false);
  error = signal<string | null>(null);
  private _stageTimer: any = null;

  private cycleStages(): void {
    const stages = [
      'searching the web…',
      'cross-checking sources…',
      'verifying domain & registry…',
      'extracting financials…',
    ];
    let i = 0;
    this.enrichStage.set(stages[0]);
    this._stageTimer = setInterval(() => {
      i = Math.min(i + 1, stages.length - 1);
      this.enrichStage.set(stages[i]);
    }, 1500);
  }
  private stopStages(): void {
    if (this._stageTimer) { clearInterval(this._stageTimer); this._stageTimer = null; }
  }

  constructor(@Inject(MAT_DIALOG_DATA) public data: StartupDetailDialogData) {}

  ngOnInit(): void {
    const fb = this.data.fallback || {};
    const baseFromFallback: StartupDetail = {
      id: '', profile_id: '', profile_url: fb.website || null,
      company_name: this.data.companyName, description: null,
      industry: fb.company_category || null, sector: null, stage: null,
      state: fb.state || null, city: null, website: fb.website || null,
      logo_url: null, badges: [], dpiit_recognised: false,
      contact_email: null, contact_phone: null, contact_address: null,
      linkedin_url: null, twitter_url: null, facebook_url: null,
      source_url: null, cin_real: null, gst: null,
      contact_enriched_at: null,
      scraped_at: fb.date_of_incorporation || null,
    };

    if (!this.data.cin || !this.data.cin.startsWith('SIH-')) {
      this.s.set(baseFromFallback);
      this.loading.set(false);
      return;
    }

    const cin = this.data.cin;
    this.http.get<StartupDetail>(`${environment.apiUrl}/startups/by-cin/${encodeURIComponent(cin)}`).subscribe({
      next: (v) => {
        this.s.set(v);
        this.loading.set(false);
        // Auto-kick enrichment if we don't yet have any enriched data
        // (no email AND no LLM-derived extras like cin/directors/capital).
        const hasExtras = !!(v.extras && Object.keys(v.extras).some(
          k => !['company_status','authorised_capital','paid_up_capital','date_of_incorporation'].includes(k)));
        if (!v.contact_email && !hasExtras) this.runEnrichment(cin);
      },
      error: () => { this.s.set(baseFromFallback); this.loading.set(false); },
    });
  }

  private _enrichAttempts = 0;
  private _maxEnrichAttempts = 1;

  private runEnrichment(cin: string): void {
    if (this._enrichAttempts >= this._maxEnrichAttempts) {
      this.enriching.set(false); this.stopStages();
      return;
    }
    this._enrichAttempts++;
    this.enriching.set(true);
    this.enrichAttempted.set(true);
    this.cycleStages();
    this.http.post<{ status: string }>(`${environment.apiUrl}/startups/enrich/${encodeURIComponent(cin)}`, {}).subscribe({
      next: (res) => {
        this.http.get<StartupDetail>(`${environment.apiUrl}/startups/by-cin/${encodeURIComponent(cin)}`).subscribe({
          next: (v) => {
            this.s.set(v);
            // Broadcast so the dashboard table updates its row in place.
            this.bus.notify(cin, v);
            // Retry if first pass came up empty (source flaky/slow) — robust UX.
            const gotAnything = !!(v.contact_email || v.contact_phone || v.website || v.linkedin_url);
            if (!gotAnything && (res?.status === 'timeout' || res?.status === 'error' || res?.status === 'enriched')
                && this._enrichAttempts < this._maxEnrichAttempts) {
              setTimeout(() => this.runEnrichment(cin), 1500);
            } else {
              this.enriching.set(false); this.stopStages();
            }
          },
          error: () => {
            if (this._enrichAttempts < this._maxEnrichAttempts) {
              setTimeout(() => this.runEnrichment(cin), 1500);
            } else {
              this.enriching.set(false); this.stopStages();
            }
          },
        });
      },
      error: () => {
        if (this._enrichAttempts < this._maxEnrichAttempts) {
          setTimeout(() => this.runEnrichment(cin), 1500);
        } else {
          this.enriching.set(false); this.stopStages();
        }
      },
    });
  }

  // Maps a CIN's 2-letter state code → canonical state name. Used to detect
  // when startupindia's listed city/state contradicts the MCA-registered state.
  private static CIN_STATE_MAP: { [k: string]: string } = {
    MH: 'Maharashtra', DL: 'Delhi', KA: 'Karnataka', TN: 'Tamil Nadu',
    TG: 'Telangana', AP: 'Andhra Pradesh', GJ: 'Gujarat', RJ: 'Rajasthan',
    UP: 'Uttar Pradesh', MP: 'Madhya Pradesh', WB: 'West Bengal',
    UT: 'Uttarakhand', UR: 'Uttarakhand', PB: 'Punjab', HR: 'Haryana',
    OR: 'Odisha', BR: 'Bihar', JH: 'Jharkhand', KL: 'Kerala',
    CT: 'Chhattisgarh', CH: 'Chandigarh', GA: 'Goa', AS: 'Assam',
    ML: 'Meghalaya', MN: 'Manipur', TR: 'Tripura', MZ: 'Mizoram',
    NL: 'Nagaland', AR: 'Arunachal Pradesh', SK: 'Sikkim',
    JK: 'Jammu and Kashmir', PY: 'Puducherry',
  };

  formatLocation(v: StartupDetail): string {
    // MCA-registered city/state (from extras, set by the enricher's CIN-anchored
    // extraction) is authoritative. Startupindia listings can be stale or list
    // a service area instead of the registered office.
    const extras = v.extras || {};
    let city = (extras as any)['city'] || v.city || '';
    let state = (extras as any)['state'] || v.state || '';
    // If CIN provides a state code, force it as the canonical state. This
    // catches the bug where startupindia says "Gwalior, MP" but CIN is UP.
    const cin = (extras as any)['cin'] || v.cin_real || '';
    if (typeof cin === 'string' && cin.length === 21) {
      const code = cin.substr(6, 2).toUpperCase();
      const mapped = StartupDetailDialogComponent.CIN_STATE_MAP[code];
      if (mapped) {
        if (state && state.toLowerCase() !== mapped.toLowerCase()) {
          // Contradiction: trust CIN. Drop the startupindia city too because
          // it likely belongs to the wrong state.
          if (v.city && v.city.toLowerCase() === (city || '').toLowerCase()) {
            city = '';
          }
        }
        state = mapped;
      }
    }
    const parts = [city, state].filter(Boolean);
    return parts.length ? parts.join(', ') : '—';
  }

  // Parse the AI Overview plain text (produced by SerpAPI's flattener) into
  // typed blocks for nice rendering. Format conventions:
  //   "## text"       → heading
  //   "- Title: text" → list item with title
  //   "- text"        → bare list item
  //   anything else   → paragraph
  parseAiOverview(raw: string): Array<{type: 'heading' | 'paragraph' | 'list', text?: string, items?: {title?: string, text: string}[]}> {
    if (!raw) return [];
    const lines = raw.split('\n').map(l => l.trim()).filter(Boolean);
    const out: any[] = [];
    let currentList: {title?: string, text: string}[] | null = null;
    const flushList = () => { if (currentList && currentList.length) out.push({type: 'list', items: currentList}); currentList = null; };
    for (const line of lines) {
      if (line.startsWith('## ')) {
        flushList();
        out.push({type: 'heading', text: line.slice(3).trim()});
      } else if (line.startsWith('- ')) {
        const body = line.slice(2).trim();
        const colon = body.indexOf(': ');
        let item: {title?: string, text: string};
        if (colon > 0 && colon < 60) {
          item = {title: body.slice(0, colon).trim(), text: body.slice(colon + 2).trim()};
        } else {
          item = {text: body};
        }
        currentList = currentList || [];
        currentList.push(item);
      } else {
        flushList();
        out.push({type: 'paragraph', text: line});
      }
    }
    flushList();
    return out;
  }

  hasAnyContact(v: StartupDetail): boolean {
    return !!(v.contact_email || v.contact_phone || v.website || v.linkedin_url || v.twitter_url || v.facebook_url);
  }

  // Keys already rendered as bespoke tiles above — exclude from the dynamic block.
  private _renderedExtraKeys = new Set([
    'founded', 'headquarters', 'founders', 'ceo', 'employees',
    'revenue', 'parent', 'type', 'snippet', 'wikipedia',
    'knowledge_panel', 'linkedin_company', 'google_ai_overview',
    // Already surfaced as bespoke tiles or via formatLocation():
    'city', 'state', 'cin',
  ]);

  dynamicExtras(v: StartupDetail): { key: string; label: string; value: string }[] {
    const ex = v.extras || {};
    const out: { key: string; label: string; value: string }[] = [];
    for (const k of Object.keys(ex)) {
      if (this._renderedExtraKeys.has(k)) continue;
      const raw = (ex as any)[k];
      if (raw === null || raw === undefined || raw === '') continue;
      const value = typeof raw === 'string' ? raw : (Array.isArray(raw) ? raw.join(', ') : String(raw));
      const label = k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      out.push({ key: k, label, value });
    }
    return out;
  }

  close(): void { this.ref.close(); }

  copyDetails(): void {
    const s = this.s();
    if (!s) return;
    const text = [
      `Company: ${s.company_name}`,
      `CIN: ${s.cin_real || '—'}`,
      `GST: ${s.gst || '—'}`,
      `Stage: ${s.stage || '—'}`,
      `Industry: ${s.industry || '—'}`,
      `Sector: ${s.sector || '—'}`,
      `Location: ${this.formatLocation(s)}`,
      `Website: ${s.website || '—'}`,
      `Email: ${s.contact_email || '—'}`,
      `Phone: ${s.contact_phone || '—'}`,
      `Address: ${s.contact_address || '—'}`,
    ].join('\n');
    navigator.clipboard.writeText(text).then(() => {
      this.snack.open('Details copied to clipboard', 'Close', { duration: 2000 });
    });
  }

  exportSingle(type: 'csv' | 'xlsx'): void {
    const s = this.s();
    if (!s) return;
    this.exporting.set(true);

    const headers = ['CIN', 'Company Name', 'GST', 'Stage', 'Industry', 'Sector', 'Location', 'Website', 'Email', 'Phone', 'Address', 'DPIIT Recognised', 'DIPP Number'];
    const row = [
      s.cin_real || '', s.company_name, s.gst || '', s.stage || '',
      s.industry || '', s.sector || '', this.formatLocation(s), s.website || '',
      s.contact_email || '', s.contact_phone || '', s.contact_address || '',
      s.dpiit_recognised ? 'Yes' : 'No', s.dipp_number || '',
    ];

    if (type === 'csv') {
      const csv = headers.join(',') + '\n' + row.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',');
      const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
      this._download(blob, `${s.company_name.replace(/[^a-z0-9]/gi, '_')}.csv`);
      this.exporting.set(false);
      this.snack.open('CSV downloaded', 'Close', { duration: 2000 });
    } else {
      let html = '<table><tr>' + headers.map(h => `<th>${h}</th>`).join('') + '</tr>';
      html += '<tr>' + row.map(v => `<td>${String(v)}</td>`).join('') + '</tr></table>';
      const blob = new Blob([html], { type: 'application/vnd.ms-excel' });
      this._download(blob, `${s.company_name.replace(/[^a-z0-9]/gi, '_')}.xls`);
      this.exporting.set(false);
      this.snack.open('Excel file downloaded', 'Close', { duration: 2000 });
    }
  }

  private _download(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }
}
