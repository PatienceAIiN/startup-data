import { Component, OnInit, OnDestroy, inject, signal, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Subject, debounceTime, distinctUntilChanged } from 'rxjs';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatChipsModule } from '@angular/material/chips';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { MatBadgeModule } from '@angular/material/badge';
import { CompanyService } from '../../core/services/company.service';
import { ScraperService } from '../../core/services/scraper.service';
import { ExportService } from '../../core/services/export.service';
import { AuthService } from '../../core/services/auth.service';
import { Company, CompanyFilter, CompanyStats } from '../../core/models/company.model';
import { ScrapeJob, ExportHistory } from '../../core/models/api-response.model';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  encapsulation: ViewEncapsulation.None,
  imports: [
    CommonModule, FormsModule, RouterLink,
    MatTableModule, MatPaginatorModule, MatInputModule, MatFormFieldModule,
    MatButtonModule, MatIconModule, MatSelectModule, MatChipsModule,
    MatCardModule, MatSnackBarModule, MatProgressBarModule,
    MatSlideToggleModule, MatTooltipModule, MatDividerModule, MatBadgeModule,
  ],
  template: `
    <div class="dashboard-root">
      <!-- Top Navigation Bar -->
      <header class="dash-navbar">
        <div class="dash-logo">
          <span class="logo-icon">🚀</span>
          <div>
            <span class="logo-title">StartupIntel</span>
            <span class="logo-sub">India B2B Intelligence</span>
          </div>
        </div>
        <div class="dash-nav-right">
          <span class="user-email">{{ auth.currentUser()?.email }}</span>
          <button mat-stroked-button class="logout-btn" (click)="auth.logout()">
            <mat-icon>logout</mat-icon>
            Logout
          </button>
        </div>
      </header>

      <main class="dash-content">

        <!-- Stats Row -->
        <section class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon stat-icon-blue">
              <mat-icon>business</mat-icon>
            </div>
            <div class="stat-body">
              <div class="stat-label">Total Companies</div>
              <div class="stat-value">{{ (stats()?.total_companies ?? 0) | number }}</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon stat-icon-green">
              <mat-icon>verified</mat-icon>
            </div>
            <div class="stat-body">
              <div class="stat-label">Matched</div>
              <div class="stat-value color-green">{{ (stats()?.matched_companies ?? 0) | number }}</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon stat-icon-purple">
              <mat-icon>rocket_launch</mat-icon>
            </div>
            <div class="stat-body">
              <div class="stat-label">Startups</div>
              <div class="stat-value color-blue">{{ (stats()?.startups ?? 0) | number }}</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon stat-icon-yellow">
              <mat-icon>analytics</mat-icon>
            </div>
            <div class="stat-body">
              <div class="stat-label">Avg Match Score</div>
              <div class="stat-value color-yellow">{{ ((stats()?.avg_match_score ?? 0) * 100) | number:'1.0-1' }}%</div>
            </div>
          </div>
        </section>

        <!-- Filters Panel -->
        <section class="filters-panel">
          <div class="filters-row">
            <mat-form-field appearance="outline" class="filter-search">
              <mat-label>Search companies</mat-label>
              <mat-icon matPrefix>search</mat-icon>
              <input matInput [(ngModel)]="searchValue" (ngModelChange)="onSearch($event)" placeholder="Company name..." />
            </mat-form-field>

            <mat-form-field appearance="outline" class="filter-date">
              <mat-label>From Date</mat-label>
              <input matInput type="date" [(ngModel)]="filter.dateFrom" (change)="loadData()" />
            </mat-form-field>

            <mat-form-field appearance="outline" class="filter-date">
              <mat-label>To Date</mat-label>
              <input matInput type="date" [(ngModel)]="filter.dateTo" (change)="loadData()" />
            </mat-form-field>

            <mat-form-field appearance="outline" class="filter-state">
              <mat-label>State</mat-label>
              <mat-select [(ngModel)]="filter.state" (ngModelChange)="onStateChange()">
                <mat-option value="">All States</mat-option>
                @for (s of topStates(); track s) {
                  <mat-option [value]="s">{{ s }}</mat-option>
                }
              </mat-select>
            </mat-form-field>

            <mat-slide-toggle
              [(ngModel)]="startupOnly"
              (change)="onStartupToggle()"
              class="startup-toggle"
            >
              Startups Only
            </mat-slide-toggle>
          </div>

          <div class="actions-row">
            <button mat-flat-button class="btn-reset" (click)="resetFilters()">
              <mat-icon>filter_alt_off</mat-icon>
              Reset
            </button>
            @if (auth.isAdmin()) {
              <button mat-flat-button class="btn-scrape" (click)="triggerScrape()" [disabled]="scraping()">
                <mat-icon>{{ scraping() ? 'hourglass_top' : 'refresh' }}</mat-icon>
                {{ scraping() ? 'Scraping...' : 'Refresh Data' }}
              </button>
            }
            <div class="spacer"></div>
            <span class="result-count">{{ total() | number }} results</span>
            <button mat-stroked-button class="btn-export" (click)="exportFile('csv')">
              <mat-icon>download</mat-icon>
              CSV
            </button>
            <button mat-stroked-button class="btn-export" (click)="exportFile('xlsx')">
              <mat-icon>table_chart</mat-icon>
              XLSX
            </button>
          </div>
        </section>

        <!-- Scrape Progress Banner -->
        @if (scraping()) {
          <div class="scrape-banner">
            <mat-progress-bar mode="indeterminate" class="scrape-bar"></mat-progress-bar>
            <div class="scrape-text">
              <mat-icon>sync</mat-icon>
              Scraping in progress...
              @if (currentJob()?.records_scraped) {
                <strong>{{ currentJob()?.records_scraped }} records scraped</strong>
              }
            </div>
          </div>
        }

        <!-- Data Table -->
        <section class="table-section">
          @if (loading()) {
            <mat-progress-bar mode="indeterminate" class="table-loader"></mat-progress-bar>
          }

          <div class="table-wrapper">
            <table mat-table [dataSource]="companies()" class="companies-table">

              <ng-container matColumnDef="company_name">
                <th mat-header-cell *matHeaderCellDef>Company Name</th>
                <td mat-cell *matCellDef="let c">
                  <a [routerLink]="['/companies', c.id]" class="company-link">
                    {{ c.company_name }}
                  </a>
                </td>
              </ng-container>

              <ng-container matColumnDef="cin">
                <th mat-header-cell *matHeaderCellDef>CIN</th>
                <td mat-cell *matCellDef="let c">
                  <span class="cin-text">{{ c.cin || '—' }}</span>
                </td>
              </ng-container>

              <ng-container matColumnDef="company_status">
                <th mat-header-cell *matHeaderCellDef>Status</th>
                <td mat-cell *matCellDef="let c">
                  @if (c.company_status === 'Active') {
                    <span class="badge badge-active">{{ c.company_status }}</span>
                  } @else {
                    <span class="badge badge-inactive">{{ c.company_status || '—' }}</span>
                  }
                </td>
              </ng-container>

              <ng-container matColumnDef="state">
                <th mat-header-cell *matHeaderCellDef>State</th>
                <td mat-cell *matCellDef="let c">{{ c.state || '—' }}</td>
              </ng-container>

              <ng-container matColumnDef="date_of_incorporation">
                <th mat-header-cell *matHeaderCellDef>Inc. Date</th>
                <td mat-cell *matCellDef="let c">{{ c.date_of_incorporation || '—' }}</td>
              </ng-container>

              <ng-container matColumnDef="match_score">
                <th mat-header-cell *matHeaderCellDef>Match</th>
                <td mat-cell *matCellDef="let c">
                  @if (c.match_score >= 0.9) {
                    <span class="badge badge-score-high">{{ (c.match_score * 100) | number:'1.0-0' }}%</span>
                  } @else if (c.match_score >= 0.75) {
                    <span class="badge badge-score-mid">{{ (c.match_score * 100) | number:'1.0-0' }}%</span>
                  } @else {
                    <span class="badge badge-score-low">{{ (c.match_score * 100) | number:'1.0-0' }}%</span>
                  }
                </td>
              </ng-container>

              <ng-container matColumnDef="is_startup">
                <th mat-header-cell *matHeaderCellDef>Startup</th>
                <td mat-cell *matCellDef="let c">
                  @if (c.is_startup) {
                    <span class="startup-yes">✓ YES</span>
                  } @else {
                    <span class="startup-no">—</span>
                  }
                </td>
              </ng-container>

              <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>

              <tr class="mat-row" *matNoDataRow>
                <td class="mat-cell no-data-cell" [attr.colspan]="displayedColumns.length">
                  @if (loading()) {
                    <div class="empty-state">Loading...</div>
                  } @else {
                    <div class="empty-state">
                      <mat-icon class="empty-icon">search_off</mat-icon>
                      <p>No companies found. Try adjusting filters or trigger a data refresh.</p>
                    </div>
                  }
                </td>
              </tr>
            </table>
          </div>

          <mat-paginator
            [length]="total()"
            [pageSize]="filter.pageSize ?? 25"
            [pageSizeOptions]="[25, 50, 100]"
            (page)="onPage($event)"
            showFirstLastButtons
          ></mat-paginator>
        </section>

        <!-- Export History -->
        @if (exportHistory().length > 0) {
          <section class="export-history">
            <h3 class="section-title">
              <mat-icon>history</mat-icon>
              Recent Exports
            </h3>
            <div class="export-list">
              @for (exp of exportHistory().slice(0, 5); track exp.id) {
                <div class="export-item">
                  <mat-icon class="export-file-icon">insert_drive_file</mat-icon>
                  <span class="export-name">{{ exp.file_name }}</span>
                  <span class="export-count">{{ exp.record_count }} records</span>
                  <a [href]="exp.r2_url" target="_blank" class="export-link">
                    <mat-icon>open_in_new</mat-icon>
                    Download
                  </a>
                </div>
              }
            </div>
          </section>
        }

      </main>
    </div>
  `,
  styles: [`
    .dashboard-root {
      min-height: 100vh;
      background: #0f172a;
      color: #f1f5f9;
      font-family: Roboto, sans-serif;
    }

    /* ---- Navbar ---- */
    .dash-navbar {
      background: #1e293b;
      border-bottom: 1px solid #334155;
      padding: 0 24px;
      height: 64px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .dash-logo {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .logo-icon {
      font-size: 28px;
      line-height: 1;
    }
    .logo-title {
      font-size: 20px;
      font-weight: 700;
      color: #34d399;
      display: block;
      line-height: 1.2;
    }
    .logo-sub {
      font-size: 11px;
      color: #64748b;
      display: block;
    }
    .dash-nav-right {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .user-email {
      color: #94a3b8;
      font-size: 13px;
    }
    .logout-btn {
      border-color: #475569 !important;
      color: #94a3b8 !important;
      font-size: 13px;
    }
    .logout-btn mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      margin-right: 4px;
    }

    /* ---- Main Content ---- */
    .dash-content {
      max-width: 1400px;
      margin: 0 auto;
      padding: 24px;
    }

    /* ---- Stats ---- */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 24px;
    }
    @media (max-width: 900px) {
      .stats-grid { grid-template-columns: repeat(2, 1fr); }
    }
    @media (max-width: 500px) {
      .stats-grid { grid-template-columns: 1fr; }
    }
    .stat-card {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 20px;
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .stat-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .stat-icon mat-icon {
      font-size: 24px;
      width: 24px;
      height: 24px;
    }
    .stat-icon-blue { background: rgba(59,130,246,0.15); color: #60a5fa; }
    .stat-icon-green { background: rgba(52,211,153,0.15); color: #34d399; }
    .stat-icon-purple { background: rgba(167,139,250,0.15); color: #a78bfa; }
    .stat-icon-yellow { background: rgba(251,191,36,0.15); color: #fbbf24; }
    .stat-label {
      font-size: 12px;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }
    .stat-value {
      font-size: 28px;
      font-weight: 700;
      color: #f1f5f9;
      line-height: 1;
    }
    .color-green { color: #34d399; }
    .color-blue { color: #60a5fa; }
    .color-yellow { color: #fbbf24; }

    /* ---- Filters Panel ---- */
    .filters-panel {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 16px 20px;
      margin-bottom: 16px;
    }
    .filters-row {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      margin-bottom: 12px;
    }
    .filter-search {
      flex: 1;
      min-width: 220px;
    }
    .filter-date {
      width: 150px;
    }
    .filter-state {
      width: 180px;
    }
    .startup-toggle {
      margin-left: 4px;
      --mdc-switch-selected-track-color: #34d399;
      --mdc-switch-selected-handle-color: #fff;
    }
    .startup-toggle .mdc-form-field > label {
      color: #94a3b8;
    }
    .actions-row {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .spacer { flex: 1; }
    .result-count {
      color: #64748b;
      font-size: 13px;
    }
    .btn-reset {
      background: #334155 !important;
      color: #94a3b8 !important;
    }
    .btn-reset mat-icon { font-size: 18px; width: 18px; height: 18px; }
    .btn-scrape {
      background: #1d4ed8 !important;
      color: #fff !important;
    }
    .btn-scrape mat-icon { font-size: 18px; width: 18px; height: 18px; }
    .btn-export {
      border-color: #10b981 !important;
      color: #34d399 !important;
    }
    .btn-export mat-icon { font-size: 18px; width: 18px; height: 18px; }

    /* ---- Scrape Banner ---- */
    .scrape-banner {
      background: rgba(29, 78, 216, 0.15);
      border: 1px solid #1d4ed8;
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 16px;
    }
    .scrape-bar { margin-bottom: 8px; }
    .scrape-text {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #93c5fd;
      font-size: 14px;
    }
    .scrape-text mat-icon { font-size: 18px; width: 18px; height: 18px; }

    /* ---- Table ---- */
    .table-section {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
      overflow: hidden;
      margin-bottom: 24px;
    }
    .table-loader {
      width: 100%;
    }
    .table-wrapper {
      overflow-x: auto;
    }
    .companies-table {
      width: 100%;
      background: transparent !important;
    }
    .companies-table th.mat-mdc-header-cell {
      background: #0f172a !important;
      color: #94a3b8 !important;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border-bottom: 1px solid #334155 !important;
      padding: 14px 16px;
      white-space: nowrap;
    }
    .companies-table td.mat-mdc-cell {
      background: transparent !important;
      color: #cbd5e1 !important;
      border-bottom: 1px solid #1e293b !important;
      padding: 12px 16px;
      font-size: 14px;
    }
    .companies-table tr.mat-mdc-row:hover td {
      background: rgba(51, 65, 85, 0.5) !important;
    }
    .company-link {
      color: #34d399;
      text-decoration: none;
      font-weight: 500;
    }
    .company-link:hover {
      text-decoration: underline;
    }
    .cin-text {
      font-family: 'Roboto Mono', monospace;
      font-size: 12px;
      color: #94a3b8;
    }

    /* Badges */
    .badge {
      padding: 3px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 600;
      display: inline-block;
    }
    .badge-active { background: #064e3b; color: #34d399; }
    .badge-inactive { background: #1e293b; color: #64748b; border: 1px solid #334155; }
    .badge-score-high { background: #064e3b; color: #34d399; }
    .badge-score-mid { background: #451a03; color: #fbbf24; }
    .badge-score-low { background: #450a0a; color: #f87171; }
    .startup-yes { color: #60a5fa; font-size: 12px; font-weight: 700; }
    .startup-no { color: #334155; font-size: 12px; }

    /* Empty state */
    .no-data-cell {
      text-align: center !important;
      border: none !important;
    }
    .empty-state {
      padding: 64px 24px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      color: #475569;
    }
    .empty-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #334155;
    }

    /* Paginator */
    mat-paginator {
      background: #1e293b !important;
      color: #94a3b8 !important;
      border-top: 1px solid #334155;
    }
    .mat-mdc-paginator-range-label,
    .mat-mdc-paginator-page-size-label {
      color: #94a3b8;
    }

    /* Export History */
    .export-history {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 20px;
    }
    .section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #94a3b8;
      font-size: 14px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin: 0 0 16px;
    }
    .section-title mat-icon { font-size: 18px; width: 18px; height: 18px; }
    .export-list { display: flex; flex-direction: column; gap: 10px; }
    .export-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 12px;
      background: #0f172a;
      border-radius: 8px;
      border: 1px solid #334155;
    }
    .export-file-icon { color: #64748b; font-size: 18px; width: 18px; height: 18px; }
    .export-name { flex: 1; color: #cbd5e1; font-size: 13px; }
    .export-count { color: #64748b; font-size: 12px; }
    .export-link {
      display: flex;
      align-items: center;
      gap: 4px;
      color: #34d399;
      text-decoration: none;
      font-size: 13px;
    }
    .export-link:hover { text-decoration: underline; }
    .export-link mat-icon { font-size: 14px; width: 14px; height: 14px; }

    /* Material form field overrides for this component */
    .mat-mdc-form-field .mdc-text-field--outlined:not(.mdc-text-field--disabled) {
      background: rgba(15, 23, 42, 0.6) !important;
    }
    .mat-mdc-form-field .mdc-notched-outline__leading,
    .mat-mdc-form-field .mdc-notched-outline__notch,
    .mat-mdc-form-field .mdc-notched-outline__trailing {
      border-color: #475569 !important;
    }
    .mat-mdc-form-field:hover .mdc-notched-outline__leading,
    .mat-mdc-form-field:hover .mdc-notched-outline__notch,
    .mat-mdc-form-field:hover .mdc-notched-outline__trailing {
      border-color: #94a3b8 !important;
    }
    .mat-mdc-form-field.mat-focused .mdc-notched-outline__leading,
    .mat-mdc-form-field.mat-focused .mdc-notched-outline__notch,
    .mat-mdc-form-field.mat-focused .mdc-notched-outline__trailing {
      border-color: #34d399 !important;
      border-width: 2px !important;
    }
    .mat-mdc-form-field .mdc-floating-label,
    .mat-mdc-form-field .mat-mdc-floating-label {
      color: #64748b !important;
    }
    .mat-mdc-form-field.mat-focused .mdc-floating-label {
      color: #34d399 !important;
    }
    .mat-mdc-form-field input.mat-mdc-input-element {
      color: #f1f5f9 !important;
    }
    .mat-mdc-form-field .mat-mdc-select-value {
      color: #f1f5f9 !important;
    }
    .mat-mdc-form-field .mat-mdc-select-arrow {
      color: #64748b !important;
    }
    .mat-mdc-form-field .mat-mdc-form-field-icon-prefix mat-icon {
      color: #64748b;
    }
  `],
})
export class DashboardComponent implements OnInit, OnDestroy {
  private companyService = inject(CompanyService);
  private scraperService = inject(ScraperService);
  private exportService = inject(ExportService);
  private snack = inject(MatSnackBar);
  auth = inject(AuthService);

  displayedColumns = ['company_name', 'cin', 'company_status', 'state', 'date_of_incorporation', 'match_score', 'is_startup'];

  companies = signal<Company[]>([]);
  total = signal(0);
  stats = signal<CompanyStats | null>(null);
  loading = signal(false);
  scraping = signal(false);
  currentJob = signal<ScrapeJob | null>(null);
  exportHistory = signal<ExportHistory[]>([]);
  topStates = signal<string[]>([]);

  filter: CompanyFilter = {
    page: 1,
    pageSize: 25,
    dateFrom: this._threeYearsAgo(),
    dateTo: new Date().toISOString().split('T')[0],
  };

  searchValue = '';
  startupOnly = false;

  private searchSubject = new Subject<string>();
  private pollInterval: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    this.loadData();
    this.loadStats();
    this.loadExportHistory();

    this.searchSubject.pipe(debounceTime(400), distinctUntilChanged()).subscribe(v => {
      this.filter.search = v || undefined;
      this.filter.page = 1;
      this.loadData();
    });
  }

  ngOnDestroy(): void {
    if (this.pollInterval) clearInterval(this.pollInterval);
  }

  private _threeYearsAgo(): string {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 3);
    return d.toISOString().split('T')[0];
  }

  loadData(): void {
    this.loading.set(true);
    this.companyService.getCompanies(this.filter).subscribe({
      next: (res) => {
        this.companies.set(res.items);
        this.total.set(res.total);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        const msg = err.error?.detail || 'Failed to load companies';
        this.snack.open(msg, 'Close', { duration: 4000 });
      },
    });
  }

  loadStats(): void {
    this.companyService.getStats().subscribe({
      next: (s) => {
        this.stats.set(s);
        this.topStates.set(Object.keys(s.by_state).slice(0, 25));
      },
      error: () => {},
    });
  }

  loadExportHistory(): void {
    this.exportService.getHistory().subscribe({
      next: (h) => this.exportHistory.set(h),
      error: () => {},
    });
  }

  onSearch(val: string): void {
    this.searchSubject.next(val);
  }

  onStateChange(): void {
    this.filter.page = 1;
    this.loadData();
  }

  onStartupToggle(): void {
    this.filter.isStartup = this.startupOnly ? true : undefined;
    this.filter.page = 1;
    this.loadData();
  }

  onPage(e: PageEvent): void {
    this.filter.page = e.pageIndex + 1;
    this.filter.pageSize = e.pageSize;
    this.loadData();
  }

  resetFilters(): void {
    this.searchValue = '';
    this.startupOnly = false;
    this.filter = {
      page: 1,
      pageSize: 25,
      dateFrom: this._threeYearsAgo(),
      dateTo: new Date().toISOString().split('T')[0],
    };
    this.loadData();
  }

  triggerScrape(): void {
    this.scraperService.trigger(this.filter.dateFrom, this.filter.dateTo).subscribe({
      next: (res) => {
        this.snack.open('Scrape job started!', 'Close', { duration: 3000 });
        this.scraping.set(true);
        this._pollJob(res.job_id);
      },
      error: (err) => {
        const msg = err.error?.detail || 'Failed to trigger scrape';
        this.snack.open(msg, 'Close', { duration: 4000 });
      },
    });
  }

  private _pollJob(jobId: string): void {
    if (this.pollInterval) clearInterval(this.pollInterval);
    this.pollInterval = setInterval(() => {
      this.scraperService.getStatus(jobId).subscribe({
        next: (job) => {
          this.currentJob.set(job);
          if (job.status === 'completed' || job.status === 'failed') {
            this.scraping.set(false);
            clearInterval(this.pollInterval!);
            if (job.status === 'completed') {
              this.snack.open(`Done! ${job.records_matched} companies matched.`, 'Close', { duration: 5000 });
              this.loadData();
              this.loadStats();
            } else {
              this.snack.open('Scrape failed: ' + job.error_message, 'Close', { duration: 6000 });
            }
          }
        },
      });
    }, 5000);
  }

  exportFile(type: 'csv' | 'xlsx'): void {
    this.snack.open('Generating export...', undefined, { duration: 2000 });
    this.exportService.export(type, this.filter.dateFrom, this.filter.dateTo, this.filter.state, this.filter.isStartup).subscribe({
      next: (res) => {
        window.open(res.download_url, '_blank');
        this.loadExportHistory();
      },
      error: () => this.snack.open('Export failed', 'Close', { duration: 3000 }),
    });
  }
}
