import { Component, Inject, OnInit, ViewEncapsulation, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatSnackBar } from '@angular/material/snack-bar';
import { CompanyService } from '../../../core/services/company.service';
import { Company } from '../../../core/models/company.model';

export interface CompanyDetailDialogData {
  companyId: string;
  initialData?: Company;
}

@Component({
  selector: 'app-company-detail-dialog',
  standalone: true,
  encapsulation: ViewEncapsulation.None,
  imports: [
    CommonModule, MatDialogModule, MatButtonModule, MatIconModule,
    MatProgressBarModule, MatTabsModule,
  ],
  template: `
    <div class="cd-dialog">
      @if (loading()) {
        <mat-progress-bar mode="indeterminate" class="cd-loader"></mat-progress-bar>
      }

      @if (company(); as c) {
        <!-- Header -->
        <div class="cd-header">
          <div class="cd-header-content">
            <div class="cd-icon-wrap">
              <mat-icon>business</mat-icon>
            </div>
            <div class="cd-header-text">
              <h2 class="cd-title">{{ c.company_name }}</h2>
              <div class="cd-badges">
                @if (c.company_status === 'Active') {
                  <span class="cd-badge cd-badge-active">
                    <span class="dot"></span>
                    {{ c.company_status }}
                  </span>
                } @else if (c.company_status) {
                  <span class="cd-badge cd-badge-inactive">{{ c.company_status }}</span>
                }
                @if (c.is_startup) {
                  <span class="cd-badge cd-badge-startup">
                    <mat-icon>rocket_launch</mat-icon>
                    Startup
                  </span>
                }
                @if (c.match_score >= 0.9) {
                  <span class="cd-badge cd-badge-score-high">{{ (c.match_score * 100) | number:'1.0-0' }}% Match</span>
                } @else if (c.match_score >= 0.75) {
                  <span class="cd-badge cd-badge-score-mid">{{ (c.match_score * 100) | number:'1.0-0' }}% Match</span>
                } @else {
                  <span class="cd-badge cd-badge-score-low">{{ (c.match_score * 100) | number:'1.0-0' }}% Match</span>
                }
              </div>
            </div>
          </div>
          <button class="cd-close-btn" (click)="close()" aria-label="Close" matTooltip="Close (Esc)">
            <mat-icon>close</mat-icon>
          </button>
        </div>

        <!-- Body -->
        <div class="cd-body">
          <!-- Quick stats row -->
          <div class="cd-quick-stats">
            <div class="cd-quick-stat">
              <mat-icon>tag</mat-icon>
              <div>
                <div class="cd-qs-label">CIN</div>
                <div class="cd-qs-value cd-mono">{{ c.cin || '—' }}</div>
              </div>
            </div>
            <div class="cd-quick-stat">
              <mat-icon>event</mat-icon>
              <div>
                <div class="cd-qs-label">Incorporated</div>
                <div class="cd-qs-value">{{ c.date_of_incorporation || '—' }}</div>
              </div>
            </div>
            <div class="cd-quick-stat">
              <mat-icon>place</mat-icon>
              <div>
                <div class="cd-qs-label">State</div>
                <div class="cd-qs-value">{{ c.state || '—' }}</div>
              </div>
            </div>
            <div class="cd-quick-stat">
              <mat-icon>account_balance</mat-icon>
              <div>
                <div class="cd-qs-label">Authorised Capital</div>
                <div class="cd-qs-value">{{ c.authorised_capital ? formatINR(c.authorised_capital) : '—' }}</div>
              </div>
            </div>
          </div>

          <!-- Detail sections -->
          <div class="cd-sections">

            <section class="cd-section">
              <h3 class="cd-section-title">
                <mat-icon>info</mat-icon>
                Company Information
              </h3>
              <div class="cd-grid">
                <div class="cd-field">
                  <div class="cd-field-label">ROC Code</div>
                  <div class="cd-field-value">{{ c.roc_code || '—' }}</div>
                </div>
                <div class="cd-field">
                  <div class="cd-field-label">Category</div>
                  <div class="cd-field-value">{{ c.company_category || '—' }}</div>
                </div>
                <div class="cd-field">
                  <div class="cd-field-label">Match Method</div>
                  <div class="cd-field-value">{{ c.match_method || '—' }}</div>
                </div>
                <div class="cd-field">
                  <div class="cd-field-label">Created</div>
                  <div class="cd-field-value">{{ c.created_at | date:'medium' }}</div>
                </div>
              </div>
            </section>

            <section class="cd-section">
              <h3 class="cd-section-title">
                <mat-icon>payments</mat-icon>
                Financial Details
              </h3>
              <div class="cd-grid">
                <div class="cd-field">
                  <div class="cd-field-label">Authorised Capital</div>
                  <div class="cd-field-value cd-money">{{ c.authorised_capital ? formatINR(c.authorised_capital) : '—' }}</div>
                </div>
                <div class="cd-field">
                  <div class="cd-field-label">Paid-Up Capital</div>
                  <div class="cd-field-value cd-money">{{ c.paid_up_capital ? formatINR(c.paid_up_capital) : '—' }}</div>
                </div>
              </div>
            </section>

            @if (c.registered_address) {
              <section class="cd-section">
                <h3 class="cd-section-title">
                  <mat-icon>home_work</mat-icon>
                  Registered Address
                </h3>
                <div class="cd-address">{{ c.registered_address }}</div>
              </section>
            }

          </div>
        </div>

        <!-- Footer / Actions -->
        <div class="cd-footer">
          <button class="cd-btn cd-btn-ghost" (click)="copyDetails()">
            <mat-icon>content_copy</mat-icon>
            Copy details
          </button>
          <div class="cd-footer-spacer"></div>
          <button class="cd-btn cd-btn-secondary" (click)="exportSingle('csv')" [disabled]="exporting()">
            <mat-icon>description</mat-icon>
            Export CSV
          </button>
          <button class="cd-btn cd-btn-secondary" (click)="exportSingle('xlsx')" [disabled]="exporting()">
            <mat-icon>grid_on</mat-icon>
            Export Excel
          </button>
          <button class="cd-btn cd-btn-primary" (click)="close()">
            <mat-icon>check</mat-icon>
            Close
          </button>
        </div>
      }

      @if (!company() && !loading()) {
        <div class="cd-error">
          <mat-icon>error_outline</mat-icon>
          <h3>Company not found</h3>
          <p>The company details could not be loaded.</p>
          <button class="cd-btn cd-btn-primary" (click)="close()">Close</button>
        </div>
      }
    </div>
  `,
  styles: [`
    .cd-dialog {
      background: var(--bg-secondary);
      color: var(--text-primary);
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      border-radius: 16px;
      animation: cd-pop-in 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes cd-pop-in {
      from { opacity: 0; transform: scale(0.96) translateY(8px); }
      to { opacity: 1; transform: scale(1) translateY(0); }
    }
    .cd-loader {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      z-index: 10;
    }

    /* Header */
    .cd-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      padding: 20px 24px;
      background: linear-gradient(135deg, rgba(52, 211, 153, 0.08) 0%, rgba(96, 165, 250, 0.05) 100%);
      border-bottom: 1px solid var(--border);
    }
    .cd-header-content {
      display: flex;
      gap: 16px;
      flex: 1;
      min-width: 0;
    }
    .cd-icon-wrap {
      width: 48px;
      height: 48px;
      min-width: 48px;
      border-radius: 12px;
      background: var(--accent-bg);
      color: var(--accent);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .cd-icon-wrap mat-icon {
      font-size: 24px;
      width: 24px;
      height: 24px;
    }
    .cd-header-text {
      flex: 1;
      min-width: 0;
    }
    .cd-title {
      font-size: 20px;
      font-weight: 700;
      margin: 0 0 8px;
      color: var(--text-primary);
      word-break: break-word;
      line-height: 1.3;
    }
    .cd-badges {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .cd-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 3px 10px;
      border-radius: 14px;
      font-size: 11px;
      font-weight: 600;
    }
    .cd-badge mat-icon {
      font-size: 12px;
      width: 12px;
      height: 12px;
    }
    .cd-badge .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: currentColor;
      animation: pulse 1.8s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }
    .cd-badge-active { background: rgba(52,211,153,0.15); color: #34d399; }
    .cd-badge-inactive { background: var(--bg-tertiary); color: var(--text-muted); }
    .cd-badge-startup { background: rgba(96,165,250,0.15); color: #60a5fa; }
    .cd-badge-score-high { background: rgba(52,211,153,0.15); color: #34d399; }
    .cd-badge-score-mid { background: rgba(251,191,36,0.15); color: #fbbf24; }
    .cd-badge-score-low { background: rgba(239,68,68,0.15); color: #f87171; }

    .cd-close-btn {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: var(--bg-tertiary);
      border: 1px solid var(--border);
      color: var(--text-secondary);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.15s;
      flex-shrink: 0;
    }
    .cd-close-btn:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
      transform: rotate(90deg);
    }
    .cd-close-btn mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
    }

    /* Body */
    .cd-body {
      flex: 1;
      overflow-y: auto;
      padding: 20px 24px;
    }

    /* Quick stats */
    .cd-quick-stats {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-bottom: 20px;
    }
    @media (max-width: 700px) {
      .cd-quick-stats { grid-template-columns: repeat(2, 1fr); }
    }
    @media (max-width: 420px) {
      .cd-quick-stats { grid-template-columns: 1fr; }
    }
    .cd-quick-stat {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px;
      background: var(--bg-tertiary);
      border: 1px solid var(--border);
      border-radius: 10px;
      min-width: 0;
    }
    .cd-quick-stat mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
      color: var(--text-muted);
      flex-shrink: 0;
    }
    .cd-qs-label {
      font-size: 10px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      font-weight: 600;
      margin-bottom: 2px;
    }
    .cd-qs-value {
      font-size: 13px;
      color: var(--text-primary);
      font-weight: 600;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .cd-mono {
      font-family: 'Roboto Mono', monospace;
      font-size: 12px;
    }

    /* Sections */
    .cd-sections {
      display: flex;
      flex-direction: column;
      gap: 18px;
    }
    .cd-section {
      background: var(--bg-tertiary);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
    }
    .cd-section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      font-weight: 700;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin: 0 0 14px;
    }
    .cd-section-title mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
      color: var(--accent);
    }
    .cd-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 14px;
    }
    @media (max-width: 600px) {
      .cd-grid { grid-template-columns: 1fr; gap: 10px; }
    }
    .cd-field-label {
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
      font-weight: 600;
    }
    .cd-field-value {
      font-size: 14px;
      color: var(--text-primary);
      word-break: break-word;
    }
    .cd-money {
      font-family: 'Roboto Mono', monospace;
      color: var(--accent);
      font-weight: 600;
    }
    .cd-address {
      font-size: 14px;
      color: var(--text-primary);
      line-height: 1.6;
      padding: 4px 0;
    }

    /* Footer */
    .cd-footer {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 16px 24px;
      border-top: 1px solid var(--border);
      background: var(--bg-primary);
      flex-wrap: wrap;
    }
    .cd-footer-spacer { flex: 1; }
    .cd-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 0 14px;
      height: 38px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
      font-family: inherit;
      border: 1.5px solid transparent;
    }
    .cd-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .cd-btn mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }
    .cd-btn-ghost {
      background: transparent;
      border-color: var(--border);
      color: var(--text-secondary);
    }
    .cd-btn-ghost:hover:not(:disabled) {
      background: var(--bg-hover);
      color: var(--text-primary);
    }
    .cd-btn-secondary {
      background: var(--bg-secondary);
      border-color: var(--accent-strong);
      color: var(--accent);
    }
    .cd-btn-secondary:hover:not(:disabled) {
      background: var(--accent-bg);
    }
    .cd-btn-primary {
      background: var(--accent-strong);
      border-color: var(--accent-strong);
      color: #fff;
    }
    .cd-btn-primary:hover:not(:disabled) {
      filter: brightness(1.1);
    }

    /* Error state */
    .cd-error {
      padding: 64px 24px;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      color: var(--text-muted);
    }
    .cd-error mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: var(--text-muted);
    }
    .cd-error h3 {
      margin: 0;
      color: var(--text-primary);
      font-size: 18px;
    }
    .cd-error p {
      margin: 0;
      font-size: 14px;
    }

    /* Mobile-specific */
    @media (max-width: 600px) {
      .cd-header { padding: 16px; }
      .cd-body { padding: 16px; }
      .cd-footer {
        padding: 12px 16px;
        gap: 6px;
      }
      .cd-btn {
        padding: 0 10px;
        font-size: 12px;
        height: 36px;
      }
      .cd-title { font-size: 17px; }
      .cd-footer-spacer { display: none; }
    }
  `],
})
export class CompanyDetailDialogComponent implements OnInit {
  private companyService = inject(CompanyService);
  private snack = inject(MatSnackBar);

  company = signal<Company | null>(null);
  loading = signal(true);
  exporting = signal(false);

  constructor(
    public dialogRef: MatDialogRef<CompanyDetailDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: CompanyDetailDialogData,
  ) {
    if (data.initialData) {
      this.company.set(data.initialData);
    }
  }

  ngOnInit(): void {
    this.companyService.getCompany(this.data.companyId).subscribe({
      next: (c) => {
        this.company.set(c);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.snack.open('Failed to load company details', 'Close', { duration: 3000 });
      },
    });
  }

  close(): void {
    this.dialogRef.close();
  }

  formatINR(amount: number): string {
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)} Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)} L`;
    return `₹${amount.toLocaleString('en-IN')}`;
  }

  copyDetails(): void {
    const c = this.company();
    if (!c) return;
    const text = [
      `Company: ${c.company_name}`,
      `CIN: ${c.cin || '—'}`,
      `Status: ${c.company_status || '—'}`,
      `State: ${c.state || '—'}`,
      `Incorporated: ${c.date_of_incorporation || '—'}`,
      `Authorised Capital: ${c.authorised_capital ? this.formatINR(c.authorised_capital) : '—'}`,
      `Paid-Up Capital: ${c.paid_up_capital ? this.formatINR(c.paid_up_capital) : '—'}`,
      `Address: ${c.registered_address || '—'}`,
    ].join('\n');
    navigator.clipboard.writeText(text).then(() => {
      this.snack.open('Details copied to clipboard', 'Close', { duration: 2000 });
    });
  }

  exportSingle(type: 'csv' | 'xlsx'): void {
    const c = this.company();
    if (!c) return;
    this.exporting.set(true);

    if (type === 'csv') {
      const headers = ['CIN', 'Company Name', 'Status', 'State', 'Inc. Date', 'Authorised Capital', 'Paid Up Capital', 'Match Score', 'Is Startup', 'Address'];
      const row = [
        c.cin || '', c.company_name, c.company_status || '', c.state || '',
        c.date_of_incorporation || '', c.authorised_capital ?? '', c.paid_up_capital ?? '',
        c.match_score, c.is_startup ? 'Yes' : 'No', c.registered_address || '',
      ];
      const csv = headers.join(',') + '\n' + row.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',');
      const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
      this._download(blob, `${c.company_name.replace(/[^a-z0-9]/gi, '_')}.csv`);
      this.exporting.set(false);
      this.snack.open('CSV downloaded', 'Close', { duration: 2000 });
    } else {
      // For XLSX, fall back to CSV with .xls extension - keeps single-record export client-side
      const headers = ['CIN', 'Company Name', 'Status', 'State', 'Inc. Date', 'Authorised Capital', 'Paid Up Capital', 'Match Score', 'Is Startup', 'Address'];
      const row = [
        c.cin || '', c.company_name, c.company_status || '', c.state || '',
        c.date_of_incorporation || '', c.authorised_capital ?? '', c.paid_up_capital ?? '',
        c.match_score, c.is_startup ? 'Yes' : 'No', c.registered_address || '',
      ];
      let html = '<table><tr>' + headers.map(h => `<th>${h}</th>`).join('') + '</tr>';
      html += '<tr>' + row.map(v => `<td>${String(v)}</td>`).join('') + '</tr></table>';
      const blob = new Blob([html], { type: 'application/vnd.ms-excel' });
      this._download(blob, `${c.company_name.replace(/[^a-z0-9]/gi, '_')}.xls`);
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
