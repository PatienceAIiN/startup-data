import { Component, OnInit, inject, signal, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { CompanyService } from '../../../core/services/company.service';
import { Company } from '../../../core/models/company.model';

@Component({
  selector: 'app-company-detail',
  standalone: true,
  encapsulation: ViewEncapsulation.None,
  imports: [CommonModule, RouterLink, MatButtonModule, MatIconModule, MatProgressBarModule],
  template: `
    <div class="detail-page">
      <div class="detail-content">

        <a routerLink="/dashboard" class="back-link">
          <mat-icon>arrow_back</mat-icon>
          Back to Dashboard
        </a>

        @if (!company() && loading()) {
          <mat-progress-bar mode="indeterminate" class="detail-loader"></mat-progress-bar>
        }

        @if (company(); as c) {
          <div class="detail-header">
            <h1 class="detail-company-name">{{ c.company_name }}</h1>
            <div class="detail-badges">
              @if (c.company_status === 'Active') {
                <span class="badge badge-active">{{ c.company_status }}</span>
              } @else if (c.company_status) {
                <span class="badge badge-inactive">{{ c.company_status }}</span>
              }
              @if (c.is_startup) {
                <span class="badge badge-startup">🚀 Startup</span>
              }
              @if (c.match_score >= 0.9) {
                <span class="badge badge-score-high">Match: {{ (c.match_score * 100) | number:'1.0-0' }}%</span>
              } @else if (c.match_score >= 0.75) {
                <span class="badge badge-score-mid">Match: {{ (c.match_score * 100) | number:'1.0-0' }}%</span>
              } @else {
                <span class="badge badge-score-low">Match: {{ (c.match_score * 100) | number:'1.0-0' }}%</span>
              }
            </div>
          </div>

          <div class="detail-grid">
            @for (field of fields(); track field.label) {
              <div class="detail-field">
                <div class="field-label">{{ field.label }}</div>
                <div class="field-value">{{ field.value || '—' }}</div>
              </div>
            }
          </div>
        }

        @if (!company() && !loading()) {
          <div class="empty-state">
            <mat-icon>error_outline</mat-icon>
            <p>Company not found.</p>
            <a routerLink="/dashboard" mat-flat-button class="btn-go-back">Go back</a>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .detail-page {
      min-height: 100vh;
      background: #0f172a;
      color: #f1f5f9;
      font-family: Roboto, sans-serif;
    }
    .detail-content {
      max-width: 900px;
      margin: 0 auto;
      padding: 32px 24px;
    }
    .back-link {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: #34d399;
      text-decoration: none;
      font-size: 14px;
      font-weight: 500;
      margin-bottom: 24px;
    }
    .back-link:hover { text-decoration: underline; }
    .back-link mat-icon { font-size: 18px; width: 18px; height: 18px; }
    .detail-loader { margin-bottom: 24px; }
    .detail-header { margin-bottom: 24px; }
    .detail-company-name {
      font-size: 28px;
      font-weight: 700;
      color: #f8fafc;
      margin: 0 0 12px;
    }
    .detail-badges {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .badge {
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
    }
    .badge-active { background: #064e3b; color: #34d399; }
    .badge-inactive { background: #1e293b; color: #64748b; border: 1px solid #334155; }
    .badge-startup { background: #1e3a5f; color: #60a5fa; }
    .badge-score-high { background: #064e3b; color: #34d399; }
    .badge-score-mid { background: #451a03; color: #fbbf24; }
    .badge-score-low { background: #450a0a; color: #f87171; }
    .detail-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
    }
    @media (max-width: 600px) {
      .detail-grid { grid-template-columns: 1fr; }
    }
    .detail-field {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 10px;
      padding: 16px;
    }
    .field-label {
      font-size: 11px;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 6px;
    }
    .field-value {
      font-size: 15px;
      color: #f1f5f9;
      word-break: break-word;
    }
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 16px;
      padding: 80px 24px;
      color: #475569;
    }
    .empty-state mat-icon { font-size: 48px; width: 48px; height: 48px; }
    .btn-go-back {
      background: #10b981 !important;
      color: #fff !important;
    }
  `],
})
export class CompanyDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private companyService = inject(CompanyService);

  company = signal<Company | null>(null);
  fields = signal<Array<{ label: string; value: string | number | null }>>([]);
  loading = signal(true);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id')!;
    this.companyService.getCompany(id).subscribe({
      next: (c) => {
        this.company.set(c);
        this.loading.set(false);
        this.fields.set([
          { label: 'CIN', value: c.cin },
          { label: 'ROC Code', value: c.roc_code },
          { label: 'Category', value: c.company_category },
          { label: 'Incorporation Date', value: c.date_of_incorporation },
          { label: 'State', value: c.state },
          { label: 'Authorised Capital', value: c.authorised_capital ? `₹${c.authorised_capital.toLocaleString('en-IN')}` : null },
          { label: 'Paid Up Capital', value: c.paid_up_capital ? `₹${c.paid_up_capital.toLocaleString('en-IN')}` : null },
          { label: 'Match Method', value: c.match_method },
          { label: 'Registered Address', value: c.registered_address },
        ]);
      },
      error: () => this.loading.set(false),
    });
  }
}
