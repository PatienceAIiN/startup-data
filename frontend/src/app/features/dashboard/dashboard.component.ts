import { Component, OnInit, OnDestroy, inject, signal, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Subject, debounceTime, distinctUntilChanged } from 'rxjs';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatMenuModule } from '@angular/material/menu';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatDividerModule } from '@angular/material/divider';
import { CompanyService } from '../../core/services/company.service';
import { ScraperService } from '../../core/services/scraper.service';
import { ExportService } from '../../core/services/export.service';
import { AuthService } from '../../core/services/auth.service';
import { ThemeService } from '../../core/services/theme.service';
import { Company, CompanyFilter, CompanyStats } from '../../core/models/company.model';
import { ScrapeJob, ExportHistory } from '../../core/models/api-response.model';
import { ConfirmDialogComponent } from '../../core/dialogs/confirm-dialog.component';
import { CompanyDetailDialogComponent } from '../companies/company-detail-dialog/company-detail-dialog.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  encapsulation: ViewEncapsulation.None,
  imports: [
    CommonModule, FormsModule, RouterLink,
    MatTableModule, MatPaginatorModule, MatInputModule, MatFormFieldModule,
    MatButtonModule, MatIconModule, MatSelectModule,
    MatCardModule, MatSnackBarModule, MatProgressBarModule,
    MatSlideToggleModule, MatTooltipModule, MatMenuModule, MatDialogModule,
    MatDividerModule,
  ],
  template: `
    <div class="dashboard-root">

      <!-- Top Navigation Bar -->
      <header class="dash-navbar">
        <div class="dash-logo">
          <span class="logo-icon">🚀</span>
          <div class="logo-stack">
            <span class="logo-title">StartupIntel</span>
            <span class="logo-sub">India B2B Intelligence</span>
          </div>
        </div>

        <div class="dash-nav-right">
          <button mat-icon-button class="theme-btn" (click)="theme.toggle()" [matTooltip]="theme.theme() === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'">
            <mat-icon>{{ theme.theme() === 'dark' ? 'light_mode' : 'dark_mode' }}</mat-icon>
          </button>

          <button mat-icon-button class="user-btn" [matMenuTriggerFor]="userMenu" matTooltip="Account">
            <mat-icon>account_circle</mat-icon>
          </button>
          <mat-menu #userMenu="matMenu" xPosition="before">
            <div class="user-menu-header">
              <div class="user-name">{{ auth.currentUser()?.full_name || 'User' }}</div>
              <div class="user-email-menu">{{ auth.currentUser()?.email }}</div>
              @if (auth.isAdmin()) {
                <span class="admin-pill">ADMIN</span>
              }
            </div>
            <mat-divider></mat-divider>
            <button mat-menu-item (click)="confirmLogout()">
              <mat-icon>logout</mat-icon>
              <span>Sign out</span>
            </button>
          </mat-menu>
        </div>
      </header>

      <main class="dash-content">

        <!-- Page Header -->
        <div class="page-header">
          <div>
            <h1 class="page-title">Dashboard</h1>
            <p class="page-subtitle">Real-time Indian company intelligence — scraped daily at 2:00 PM IST</p>
          </div>
          <div class="page-actions">
            @if (auth.isAdmin()) {
              <button mat-flat-button class="btn-primary" (click)="triggerScrape()" [disabled]="scraping()">
                <mat-icon>{{ scraping() ? 'hourglass_top' : 'cloud_sync' }}</mat-icon>
                <span>{{ scraping() ? 'Scraping…' : 'Run Scrape Now' }}</span>
              </button>
            }
          </div>
        </div>

        <!-- Stats Row -->
        <section class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon stat-icon-blue"><mat-icon>business</mat-icon></div>
            <div class="stat-body">
              <div class="stat-label">Total Companies</div>
              <div class="stat-value">{{ (stats()?.total_companies ?? 0) | number }}</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon stat-icon-green"><mat-icon>verified</mat-icon></div>
            <div class="stat-body">
              <div class="stat-label">Matched</div>
              <div class="stat-value c-green">{{ (stats()?.matched_companies ?? 0) | number }}</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon stat-icon-purple"><mat-icon>rocket_launch</mat-icon></div>
            <div class="stat-body">
              <div class="stat-label">Startups</div>
              <div class="stat-value c-blue">{{ (stats()?.startups ?? 0) | number }}</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon stat-icon-yellow"><mat-icon>insights</mat-icon></div>
            <div class="stat-body">
              <div class="stat-label">Avg Match Score</div>
              <div class="stat-value c-yellow">{{ ((stats()?.avg_match_score ?? 0) * 100) | number:'1.0-1' }}%</div>
            </div>
          </div>
        </section>

        <!-- Filters Panel - Redesigned -->
        <section class="filters-panel">

          <!-- Search Bar (Hero) -->
          <div class="search-hero">
            <div class="search-input-wrap">
              <mat-icon class="search-icon">search</mat-icon>
              <input
                type="text"
                class="search-input"
                [(ngModel)]="searchValue"
                (ngModelChange)="onSearch($event)"
                placeholder="Search by company name, CIN, or category…"
              />
              @if (searchValue) {
                <button class="search-clear" (click)="clearSearch()" matTooltip="Clear search">
                  <mat-icon>close</mat-icon>
                </button>
              }
            </div>
            <button class="btn-filter-toggle" (click)="filtersOpen = !filtersOpen" [class.active]="filtersOpen">
              <mat-icon>tune</mat-icon>
              <span>Filters</span>
              @if (activeFilterCount() > 0) {
                <span class="filter-badge">{{ activeFilterCount() }}</span>
              }
            </button>
          </div>

          <!-- Advanced Filters (collapsible) -->
          @if (filtersOpen) {
            <div class="filters-advanced">
              <div class="filter-group">
                <label class="filter-label">
                  <mat-icon>event</mat-icon>
                  Date Range
                </label>
                <div class="date-range-row">
                  <div class="date-input-wrap">
                    <span class="date-prefix">From</span>
                    <input
                      type="date"
                      class="date-input"
                      [(ngModel)]="filter.dateFrom"
                      (change)="loadData()"
                    />
                  </div>
                  <span class="date-arrow">→</span>
                  <div class="date-input-wrap">
                    <span class="date-prefix">To</span>
                    <input
                      type="date"
                      class="date-input"
                      [(ngModel)]="filter.dateTo"
                      (change)="loadData()"
                    />
                  </div>
                </div>
                <!-- Quick presets -->
                <div class="date-presets">
                  <button
                    type="button"
                    class="preset-chip"
                    [class.active]="datePreset === '30d'"
                    (click)="setDatePreset('30d')"
                  >Last 30d</button>
                  <button
                    type="button"
                    class="preset-chip"
                    [class.active]="datePreset === '90d'"
                    (click)="setDatePreset('90d')"
                  >Last 90d</button>
                  <button
                    type="button"
                    class="preset-chip"
                    [class.active]="datePreset === '1y'"
                    (click)="setDatePreset('1y')"
                  >Last year</button>
                  <button
                    type="button"
                    class="preset-chip"
                    [class.active]="datePreset === '3y'"
                    (click)="setDatePreset('3y')"
                  >Last 3 years</button>
                  <button
                    type="button"
                    class="preset-chip"
                    [class.active]="datePreset === 'all'"
                    (click)="setDatePreset('all')"
                  >All time</button>
                </div>
              </div>

              <div class="filter-group">
                <label class="filter-label">
                  <mat-icon>place</mat-icon>
                  State
                </label>
                <mat-form-field appearance="outline" class="state-select-field">
                  <mat-select [(ngModel)]="filter.state" (ngModelChange)="onStateChange()" placeholder="All states">
                    <mat-option value="">All States</mat-option>
                    @for (s of topStates(); track s) {
                      <mat-option [value]="s">{{ s }}</mat-option>
                    }
                  </mat-select>
                </mat-form-field>
              </div>

              <div class="filter-group">
                <label class="filter-label">
                  <mat-icon>category</mat-icon>
                  Type
                </label>
                <div class="segmented-control">
                  <button
                    type="button"
                    class="seg-btn"
                    [class.active]="!startupOnly"
                    (click)="setStartupFilter(false)"
                  >All Companies</button>
                  <button
                    type="button"
                    class="seg-btn"
                    [class.active]="startupOnly"
                    (click)="setStartupFilter(true)"
                  >
                    <mat-icon>rocket_launch</mat-icon>
                    Startups Only
                  </button>
                </div>
              </div>
            </div>
          }

          <!-- Action Row -->
          <div class="actions-row">
            <div class="result-info">
              <span class="result-num">{{ total() | number }}</span>
              <span class="result-text">{{ total() === 1 ? 'company' : 'companies' }}</span>
              @if (activeFilterCount() > 0) {
                <button class="reset-link" (click)="resetFilters()">
                  <mat-icon>refresh</mat-icon>
                  Reset filters
                </button>
              }
            </div>
            <div class="spacer"></div>
            <div class="export-group">
              <span class="export-label">Export:</span>
              <button class="btn-export" (click)="exportFile('csv')" [disabled]="total() === 0">
                <mat-icon>description</mat-icon>
                CSV
              </button>
              <button class="btn-export" (click)="exportFile('xlsx')" [disabled]="total() === 0">
                <mat-icon>grid_on</mat-icon>
                Excel
              </button>
            </div>
          </div>
        </section>

        <!-- Scrape Progress Banner -->
        @if (scraping()) {
          <div class="scrape-banner">
            <div class="scrape-text">
              <mat-icon class="spin-icon">sync</mat-icon>
              <span>Scraping in progress…</span>
              @if (currentJob()?.records_scraped) {
                <strong>{{ currentJob()?.records_scraped | number }} records scraped</strong>
              }
            </div>
            <mat-progress-bar mode="indeterminate"></mat-progress-bar>
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
                  <button class="company-link" (click)="openCompanyDialog(c)">{{ c.company_name }}</button>
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

              <tr class="mat-row no-data-row" *matNoDataRow>
                <td class="mat-cell no-data-cell" [attr.colspan]="displayedColumns.length">
                  @if (loading()) {
                    <div class="empty-state">Loading companies…</div>
                  } @else {
                    <div class="empty-state">
                      <mat-icon class="empty-icon">database</mat-icon>
                      <h3>No companies yet</h3>
                      <p>
                        @if (auth.isAdmin()) {
                          Click <strong>Run Scrape Now</strong> above to fetch data from Zauba Corp & data.gov.in.
                          Auto-scrape runs daily at 2:00 PM IST.
                        } @else {
                          Data will appear here once an admin runs the scraper. Auto-scrape runs daily at 2:00 PM IST.
                        }
                      </p>
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
                  <span class="export-count">{{ exp.record_count | number }} records</span>
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
    /* Use CSS variables from styles.scss */
    .dashboard-root {
      min-height: 100vh;
      background: var(--bg-primary);
      color: var(--text-primary);
      font-family: Roboto, sans-serif;
    }

    /* ---- Navbar ---- */
    .dash-navbar {
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border);
      padding: 0 24px;
      height: 64px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    @media (max-width: 600px) {
      .dash-navbar { padding: 0 12px; }
      .logo-sub { display: none; }
      .logo-title { font-size: 18px; }
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
    .logo-stack {
      display: flex;
      flex-direction: column;
      line-height: 1.2;
    }
    .logo-title {
      font-size: 20px;
      font-weight: 700;
      color: var(--accent);
    }
    .logo-sub {
      font-size: 11px;
      color: var(--text-muted);
    }
    .dash-nav-right {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .theme-btn,
    .user-btn {
      color: var(--text-secondary) !important;
    }
    .theme-btn:hover,
    .user-btn:hover {
      color: var(--accent) !important;
    }

    /* User menu */
    .user-menu-header {
      padding: 12px 16px;
      min-width: 220px;
    }
    .user-name {
      font-weight: 600;
      color: var(--text-primary);
      font-size: 14px;
    }
    .user-email-menu {
      color: var(--text-secondary);
      font-size: 12px;
      margin-top: 2px;
    }
    .admin-pill {
      display: inline-block;
      margin-top: 6px;
      padding: 2px 8px;
      background: var(--accent-bg);
      color: var(--accent);
      border-radius: 12px;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.5px;
    }

    /* ---- Main Content ---- */
    .dash-content {
      max-width: 1400px;
      margin: 0 auto;
      padding: 24px;
    }
    @media (max-width: 600px) {
      .dash-content { padding: 16px 12px; }
    }

    /* Page Header */
    .page-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
      gap: 16px;
      flex-wrap: wrap;
    }
    @media (max-width: 600px) {
      .page-header { gap: 10px; }
      .page-actions { width: 100%; }
      .page-actions .btn-primary { width: 100%; justify-content: center; }
    }
    .page-title {
      font-size: 24px;
      font-weight: 700;
      margin: 0;
      color: var(--text-primary);
    }
    @media (max-width: 600px) {
      .page-title { font-size: 20px; }
      .page-subtitle { font-size: 12px; }
    }
    .page-subtitle {
      margin: 4px 0 0;
      color: var(--text-muted);
      font-size: 13px;
    }
    .btn-primary {
      background: var(--accent-strong) !important;
      color: #fff !important;
      height: 40px;
      font-weight: 600;
    }
    .btn-primary mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      margin-right: 6px;
    }
    .btn-primary:disabled {
      background: var(--border) !important;
      color: var(--text-muted) !important;
    }

    /* ---- Stats ---- */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 20px;
    }
    @media (max-width: 900px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 500px) { .stats-grid { grid-template-columns: 1fr; } }
    .stat-card {
      background: var(--bg-secondary);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      display: flex;
      align-items: center;
      gap: 16px;
      transition: border-color 0.2s, transform 0.2s;
    }
    .stat-card:hover {
      border-color: var(--border-strong);
      transform: translateY(-2px);
    }
    .stat-icon {
      width: 48px;
      height: 48px;
      min-width: 48px;
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
    .stat-body { flex: 1; min-width: 0; }
    .stat-label {
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
      font-weight: 600;
    }
    .stat-value {
      font-size: 28px;
      font-weight: 700;
      color: var(--text-primary);
      line-height: 1.1;
    }
    .c-green { color: #34d399 !important; }
    .c-blue { color: #60a5fa !important; }
    .c-yellow { color: #fbbf24 !important; }

    /* ============================================
       REDESIGNED FILTERS PANEL
       ============================================ */
    .filters-panel {
      background: var(--bg-secondary);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      margin-bottom: 16px;
    }

    /* Search Hero - large bar at top */
    .search-hero {
      display: flex;
      gap: 12px;
      align-items: stretch;
    }
    @media (max-width: 480px) {
      .search-hero { flex-direction: column; gap: 8px; }
      .btn-filter-toggle { justify-content: center; }
    }
    .search-input-wrap {
      flex: 1;
      position: relative;
      display: flex;
      align-items: center;
      background: var(--bg-tertiary);
      border: 1.5px solid var(--border);
      border-radius: 10px;
      transition: border-color 0.15s, box-shadow 0.15s;
      height: 48px;
    }
    .search-input-wrap:hover {
      border-color: var(--border-strong);
    }
    .search-input-wrap:focus-within {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(52, 211, 153, 0.12);
    }
    .search-icon {
      position: absolute;
      left: 14px;
      color: var(--text-muted);
      font-size: 22px;
      width: 22px;
      height: 22px;
      pointer-events: none;
    }
    .search-input-wrap:focus-within .search-icon {
      color: var(--accent);
    }
    .search-input {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      padding: 0 44px 0 48px;
      height: 100%;
      font-size: 15px;
      color: var(--text-primary);
      font-family: inherit;
    }
    .search-input::placeholder {
      color: var(--text-muted);
    }
    .search-clear {
      position: absolute;
      right: 8px;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      border: none;
      background: var(--bg-hover);
      color: var(--text-muted);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s;
    }
    .search-clear:hover {
      background: var(--border);
      color: var(--text-primary);
    }
    .search-clear mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }

    /* Filter Toggle Button */
    .btn-filter-toggle {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 0 18px;
      height: 48px;
      background: var(--bg-tertiary);
      border: 1.5px solid var(--border);
      border-radius: 10px;
      color: var(--text-primary);
      font-size: 14px;
      font-weight: 500;
      font-family: inherit;
      cursor: pointer;
      transition: all 0.15s;
      white-space: nowrap;
    }
    .btn-filter-toggle:hover {
      border-color: var(--border-strong);
    }
    .btn-filter-toggle.active {
      background: var(--accent-bg);
      border-color: var(--accent);
      color: var(--accent);
    }
    .btn-filter-toggle mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }
    .filter-badge {
      background: var(--accent);
      color: #fff;
      font-size: 11px;
      font-weight: 700;
      min-width: 20px;
      height: 20px;
      padding: 0 6px;
      border-radius: 10px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    /* Advanced Filters - revealed */
    .filters-advanced {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 24px;
      padding: 20px 4px 8px;
      margin-top: 16px;
      border-top: 1px solid var(--border);
      animation: slide-down 0.2s ease-out;
    }
    @keyframes slide-down {
      from { opacity: 0; transform: translateY(-4px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @media (max-width: 1000px) {
      .filters-advanced { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 700px) {
      .filters-advanced { grid-template-columns: 1fr; gap: 16px; }
    }

    .filter-group {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .filter-label {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.6px;
    }
    .filter-label mat-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
    }

    /* Date Range */
    .date-range-row {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .date-input-wrap {
      flex: 1;
      display: flex;
      align-items: center;
      background: var(--bg-tertiary);
      border: 1.5px solid var(--border);
      border-radius: 8px;
      padding: 0 10px;
      height: 40px;
      transition: border-color 0.15s;
    }
    .date-input-wrap:hover { border-color: var(--border-strong); }
    .date-input-wrap:focus-within {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(52, 211, 153, 0.10);
    }
    .date-prefix {
      color: var(--text-muted);
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      margin-right: 8px;
    }
    .date-input {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      color: var(--text-primary);
      font-size: 13px;
      font-family: inherit;
      width: 100%;
    }
    .date-arrow {
      color: var(--text-muted);
      font-size: 16px;
      font-weight: 600;
    }
    .date-presets {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 4px;
    }
    .preset-chip {
      padding: 5px 12px;
      background: var(--bg-tertiary);
      border: 1px solid var(--border);
      border-radius: 16px;
      color: var(--text-secondary);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s;
      font-family: inherit;
    }
    .preset-chip:hover {
      border-color: var(--border-strong);
      color: var(--text-primary);
    }
    .preset-chip.active {
      background: var(--accent-bg);
      border-color: var(--accent);
      color: var(--accent);
    }

    /* State select */
    .state-select-field {
      width: 100%;
    }
    .state-select-field .mat-mdc-form-field-subscript-wrapper {
      display: none;
    }

    /* Segmented Control */
    .segmented-control {
      display: flex;
      background: var(--bg-tertiary);
      border: 1.5px solid var(--border);
      border-radius: 10px;
      padding: 3px;
      gap: 2px;
      height: 44px;
    }
    .seg-btn {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      background: transparent;
      border: none;
      border-radius: 7px;
      color: var(--text-secondary);
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s;
      font-family: inherit;
      padding: 0 12px;
    }
    .seg-btn:hover:not(.active) {
      color: var(--text-primary);
    }
    .seg-btn.active {
      background: var(--bg-secondary);
      color: var(--accent);
      box-shadow: 0 1px 3px var(--shadow);
    }
    .seg-btn mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }

    /* Action Row */
    .actions-row {
      display: flex;
      align-items: center;
      gap: 14px;
      flex-wrap: wrap;
      margin-top: 16px;
      padding-top: 14px;
      border-top: 1px solid var(--border);
    }
    @media (max-width: 600px) {
      .actions-row { gap: 10px; }
      .export-group { width: 100%; justify-content: flex-end; }
    }
    .spacer { flex: 1; }
    .result-info {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .result-num {
      font-size: 18px;
      font-weight: 700;
      color: var(--text-primary);
    }
    .result-text {
      color: var(--text-muted);
      font-size: 13px;
    }
    .reset-link {
      display: flex;
      align-items: center;
      gap: 4px;
      background: transparent;
      border: none;
      color: var(--accent);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 6px;
      font-family: inherit;
      margin-left: 8px;
      transition: background 0.15s;
    }
    .reset-link:hover {
      background: var(--accent-bg);
    }
    .reset-link mat-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
    }

    /* Export group */
    .export-group {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .export-label {
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-right: 4px;
    }
    .btn-export {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 0 14px;
      height: 36px;
      background: var(--bg-tertiary);
      border: 1.5px solid var(--accent-strong);
      border-radius: 8px;
      color: var(--accent);
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
      font-family: inherit;
    }
    .btn-export:hover:not(:disabled) {
      background: var(--accent-bg);
    }
    .btn-export:disabled {
      border-color: var(--border) !important;
      color: var(--text-muted) !important;
      cursor: not-allowed;
      opacity: 0.6;
    }
    .btn-export mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }

    /* ---- Scrape Banner ---- */
    .scrape-banner {
      background: rgba(29, 78, 216, 0.12);
      border: 1px solid #1d4ed8;
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 16px;
    }
    .scrape-text {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #93c5fd;
      font-size: 14px;
      margin-bottom: 10px;
    }
    .scrape-text mat-icon { font-size: 18px; width: 18px; height: 18px; }
    .scrape-text strong { color: #dbeafe; margin-left: auto; }
    .spin-icon {
      animation: spin 1.5s linear infinite;
    }
    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }

    /* ---- Table ---- */
    .table-section {
      background: var(--bg-secondary);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      margin-bottom: 24px;
    }
    .table-loader { width: 100%; }
    .table-wrapper {
      overflow-x: auto;
    }
    .companies-table {
      width: 100%;
      background: transparent !important;
    }
    .companies-table th.mat-mdc-header-cell {
      background: var(--bg-tertiary) !important;
      color: var(--text-secondary) !important;
      padding: 14px 16px;
      white-space: nowrap;
    }
    .companies-table td.mat-mdc-cell {
      background: transparent !important;
      color: var(--text-primary) !important;
      padding: 12px 16px;
      font-size: 14px;
    }
    @media (max-width: 600px) {
      .companies-table th.mat-mdc-header-cell,
      .companies-table td.mat-mdc-cell {
        padding: 10px 12px;
        font-size: 13px;
      }
    }
    .companies-table tr.mat-mdc-row:hover td {
      background: var(--bg-hover) !important;
    }
    .company-link {
      background: transparent;
      border: none;
      padding: 0;
      color: var(--accent);
      font-weight: 500;
      font-family: inherit;
      font-size: 14px;
      cursor: pointer;
      text-align: left;
      transition: color 0.15s;
    }
    .company-link:hover {
      text-decoration: underline;
      color: var(--accent-strong);
    }
    .cin-text {
      font-family: 'Roboto Mono', monospace;
      font-size: 12px;
      color: var(--text-muted);
    }

    /* Badges */
    .badge {
      padding: 3px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 600;
      display: inline-block;
      white-space: nowrap;
    }
    .badge-active { background: rgba(52,211,153,0.15); color: #34d399; }
    .badge-inactive { background: var(--bg-tertiary); color: var(--text-muted); border: 1px solid var(--border); }
    .badge-score-high { background: rgba(52,211,153,0.15); color: #34d399; }
    .badge-score-mid { background: rgba(251,191,36,0.15); color: #fbbf24; }
    .badge-score-low { background: rgba(239,68,68,0.15); color: #f87171; }
    .startup-yes { color: #60a5fa; font-size: 12px; font-weight: 700; }
    .startup-no { color: var(--text-muted); font-size: 12px; }

    /* Empty state */
    .no-data-row { background: transparent !important; }
    .no-data-cell {
      text-align: center !important;
      border: none !important;
      padding: 0 !important;
    }
    .empty-state {
      padding: 64px 24px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      color: var(--text-muted);
      max-width: 480px;
      margin: 0 auto;
    }
    .empty-state h3 {
      color: var(--text-primary);
      font-size: 18px;
      margin: 8px 0 0;
      font-weight: 600;
    }
    .empty-state p {
      color: var(--text-muted);
      margin: 0;
      font-size: 14px;
      line-height: 1.5;
    }
    .empty-state strong {
      color: var(--accent);
    }
    .empty-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: var(--border-strong);
    }

    /* Export History */
    .export-history {
      background: var(--bg-secondary);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
    }
    .section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--text-secondary);
      font-size: 13px;
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
      padding: 10px 14px;
      background: var(--bg-tertiary);
      border-radius: 8px;
      border: 1px solid var(--border);
    }
    .export-file-icon { color: var(--text-muted); font-size: 18px; width: 18px; height: 18px; }
    .export-name { flex: 1; color: var(--text-primary); font-size: 13px; word-break: break-all; }
    .export-count { color: var(--text-muted); font-size: 12px; white-space: nowrap; }
    .export-link {
      display: flex;
      align-items: center;
      gap: 4px;
      color: var(--accent);
      text-decoration: none;
      font-size: 13px;
      font-weight: 500;
    }
    .export-link:hover { text-decoration: underline; }
    .export-link mat-icon { font-size: 14px; width: 14px; height: 14px; }
  `],
})
export class DashboardComponent implements OnInit, OnDestroy {
  private companyService = inject(CompanyService);
  private scraperService = inject(ScraperService);
  private exportService = inject(ExportService);
  private snack = inject(MatSnackBar);
  private dialog = inject(MatDialog);
  auth = inject(AuthService);
  theme = inject(ThemeService);

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
  filtersOpen = false;
  datePreset: '30d' | '90d' | '1y' | '3y' | 'all' | 'custom' = '3y';

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
    this.datePreset = '3y';
    this.filter = {
      page: 1,
      pageSize: 25,
      dateFrom: this._threeYearsAgo(),
      dateTo: new Date().toISOString().split('T')[0],
    };
    this.loadData();
  }

  clearSearch(): void {
    this.searchValue = '';
    this.searchSubject.next('');
  }

  setDatePreset(preset: '30d' | '90d' | '1y' | '3y' | 'all'): void {
    this.datePreset = preset;
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];
    const subtract = (days: number) => {
      const d = new Date();
      d.setDate(d.getDate() - days);
      return d.toISOString().split('T')[0];
    };
    switch (preset) {
      case '30d': this.filter.dateFrom = subtract(30); this.filter.dateTo = todayStr; break;
      case '90d': this.filter.dateFrom = subtract(90); this.filter.dateTo = todayStr; break;
      case '1y':  this.filter.dateFrom = subtract(365); this.filter.dateTo = todayStr; break;
      case '3y':  this.filter.dateFrom = subtract(365 * 3); this.filter.dateTo = todayStr; break;
      case 'all': this.filter.dateFrom = undefined; this.filter.dateTo = undefined; break;
    }
    this.filter.page = 1;
    this.loadData();
  }

  setStartupFilter(only: boolean): void {
    this.startupOnly = only;
    this.filter.isStartup = only ? true : undefined;
    this.filter.page = 1;
    this.loadData();
  }

  activeFilterCount(): number {
    let n = 0;
    if (this.searchValue) n++;
    if (this.filter.state) n++;
    if (this.startupOnly) n++;
    if (this.datePreset !== '3y') n++;
    return n;
  }

  triggerScrape(): void {
    this.scraperService.trigger(this.filter.dateFrom, this.filter.dateTo).subscribe({
      next: (res) => {
        this.snack.open('Scrape job started! This may take several minutes.', 'Close', { duration: 4000 });
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
    this.snack.open('Generating export…', undefined, { duration: 2000 });
    this.exportService.export(type, this.filter.dateFrom, this.filter.dateTo, this.filter.state, this.filter.isStartup).subscribe({
      next: (res) => {
        window.open(res.download_url, '_blank');
        this.loadExportHistory();
      },
      error: () => this.snack.open('Export failed', 'Close', { duration: 3000 }),
    });
  }

  openCompanyDialog(c: Company): void {
    this.dialog.open(CompanyDetailDialogComponent, {
      data: { companyId: c.id, initialData: c },
      panelClass: 'company-detail-panel',
      width: '720px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      autoFocus: false,
    });
  }

  confirmLogout(): void {
    const ref = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: 'Sign out?',
        message: `You'll need to sign in again to access the dashboard.`,
        confirmText: 'Sign out',
        cancelText: 'Stay',
        icon: 'logout',
        variant: 'danger',
      },
      panelClass: 'custom-dialog',
      width: '400px',
    });
    ref.afterClosed().subscribe(ok => {
      if (ok) this.auth.logout();
    });
  }
}
