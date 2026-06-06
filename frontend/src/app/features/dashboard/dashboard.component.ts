import { Component, OnInit, OnDestroy, inject, signal, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
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
import { StartupDetailDialogComponent } from '../companies/startup-detail-dialog/startup-detail-dialog.component';
import { EnrichmentBusService } from '../../core/services/enrichment-bus.service';

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
          <mat-icon class="logo-icon">hub</mat-icon>
          <div class="logo-stack">
            <span class="logo-title">Nexus Intel</span>
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
          </div>
          <div class="page-actions">
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
          <div class="stat-card" data-tour="stats-startups">
            <div class="stat-icon stat-icon-purple"><mat-icon>rocket_launch</mat-icon></div>
            <div class="stat-body">
              <div class="stat-label">Startups</div>
              <div class="stat-value c-blue">{{ (stats()?.startups ?? 0) | number }}</div>
            </div>
          </div>
          <div class="stat-card stat-card-live">
            <div class="stat-icon stat-icon-green"><mat-icon>autorenew</mat-icon></div>
            <div class="stat-body">
              <div class="stat-label">
                Live updates
                <span class="live-dot" aria-hidden="true"></span>
              </div>
              <div class="stat-value c-green stat-live-text">Pulling in new startups continuously</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon stat-icon-yellow"><mat-icon>workspaces</mat-icon></div>
            <div class="stat-body">
              <div class="stat-label">Coverage</div>
              <div class="stat-value c-yellow">{{ (allStates().length || 0) }} states</div>
            </div>
          </div>
        </section>

        <!-- Filters Panel - Redesigned -->
        <section class="filters-panel">

          <!-- Search Bar (Hero) -->
          <div class="search-hero">
            <div class="search-input-wrap" data-tour="search-box">
              <mat-icon class="search-icon">search</mat-icon>
              <input
                type="text"
                class="search-input"
                [(ngModel)]="searchValue"
                (keyup.enter)="executeSearch()"
                placeholder="Search by company name, CIN, or category…"
              />
              @if (searchValue) {
                <button class="search-clear" (click)="clearSearch()" matTooltip="Clear search">
                  <mat-icon>close</mat-icon>
                </button>
              }
              <button mat-icon-button class="search-submit-btn" (click)="executeSearch()" matTooltip="Search">
                <mat-icon>keyboard_return</mat-icon>
              </button>
            </div>
            <button class="btn-filter-toggle" (click)="filtersOpen = !filtersOpen" [class.active]="filtersOpen" data-tour="filter-toggle">
              <mat-icon>tune</mat-icon>
              <span>Filters</span>
              @if (activeFilterCount() > 0) {
                <span class="filter-badge">{{ activeFilterCount() }}</span>
              }
            </button>
            <button class="btn-filter-toggle tour-btn" (click)="startTour()" matTooltip="Show me around">
              <mat-icon>tour</mat-icon>
              <span>Tour</span>
            </button>
          </div>

          <!-- Advanced Filters (collapsible) -->
          @if (filtersOpen) {
            <div class="filters-advanced">
              <div class="filter-group" data-tour="filter-state">
                <label class="filter-label">
                  <mat-icon>place</mat-icon>
                  State
                </label>
                <mat-form-field appearance="outline" class="state-select-field">
                  <mat-select [(ngModel)]="filter.state" (ngModelChange)="onStateChange()" placeholder="All states">
                    <mat-option [value]="undefined">All States</mat-option>
                    @for (s of allStates(); track s) {
                      <mat-option [value]="s">{{ s }}</mat-option>
                    }
                  </mat-select>
                </mat-form-field>
              </div>

              <div class="filter-group" data-tour="filter-city">
                <label class="filter-label">
                  <mat-icon>apartment</mat-icon>
                  City
                </label>
                <mat-form-field appearance="outline" class="state-select-field">
                  <mat-select [(ngModel)]="filter.city" (ngModelChange)="onCityChange()" [disabled]="!filter.state" placeholder="{{ filter.state ? 'All cities in ' + filter.state : 'Select a state first' }}">
                    <mat-option [value]="undefined">All Cities</mat-option>
                    @for (c of allCities(); track c) {
                      <mat-option [value]="c">{{ c }}</mat-option>
                    }
                  </mat-select>
                </mat-form-field>
              </div>

              <div class="filter-group" data-tour="segmented-type">
                <label class="filter-label">
                  <mat-icon>category</mat-icon>
                  Type
                </label>
                <div class="segmented-control">
                  <button
                    type="button"
                    class="seg-btn"
                    [class.active]="startupFilter === 'companies'"
                    (click)="setStartupFilter('companies')"
                  >Companies</button>
                  <button
                    type="button"
                    class="seg-btn"
                    [class.active]="startupFilter === 'startups'"
                    (click)="setStartupFilter('startups')"
                  >
                    <mat-icon>rocket_launch</mat-icon>
                    Startups
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

              <ng-container matColumnDef="company_category">
                <th mat-header-cell *matHeaderCellDef>Category</th>
                <td mat-cell *matCellDef="let c">{{ c.company_category || '—' }}</td>
              </ng-container>

              <ng-container matColumnDef="authorised_capital">
                <th mat-header-cell *matHeaderCellDef>Auth. Capital</th>
                <td mat-cell *matCellDef="let c">
                  {{ c.authorised_capital ? '₹' + (c.authorised_capital | number) : '—' }}
                </td>
              </ng-container>

              <ng-container matColumnDef="paid_up_capital">
                <th mat-header-cell *matHeaderCellDef>Paid Capital</th>
                <td mat-cell *matCellDef="let c">
                  {{ c.paid_up_capital ? '₹' + (c.paid_up_capital | number) : '—' }}
                </td>
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

              <!-- Startup-only columns -->
              <ng-container matColumnDef="city">
                <th mat-header-cell *matHeaderCellDef>City</th>
                <td mat-cell *matCellDef="let c">{{ startupInfo(c)?.city || '—' }}</td>
              </ng-container>

              <ng-container matColumnDef="industry">
                <th mat-header-cell *matHeaderCellDef>Industry</th>
                <td mat-cell *matCellDef="let c">{{ startupInfo(c)?.industry || c.company_category || '—' }}</td>
              </ng-container>

              <ng-container matColumnDef="contact_email">
                <th mat-header-cell *matHeaderCellDef>Email</th>
                <td mat-cell *matCellDef="let c">
                  @if (startupInfo(c)?.contact_email) {
                    <a [href]="'mailto:' + startupInfo(c)!.contact_email" class="website-link">{{ startupInfo(c)!.contact_email }}</a>
                  } @else {
                    <span class="startup-no">—</span>
                  }
                </td>
              </ng-container>

              <ng-container matColumnDef="contact_phone">
                <th mat-header-cell *matHeaderCellDef>Phone</th>
                <td mat-cell *matCellDef="let c">{{ startupInfo(c)?.contact_phone || '—' }}</td>
              </ng-container>

              <ng-container matColumnDef="dpiit">
                <th mat-header-cell *matHeaderCellDef>DPIIT</th>
                <td mat-cell *matCellDef="let c">
                  @if (startupInfo(c)?.dpiit_recognised) {
                    <span class="startup-yes">✓</span>
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
                      <h3>No results</h3>
                      <p>Try a different search or adjust your filters.</p>
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

      <!-- Tutorial Overlay -->
      @if (tourOpen()) {
        <div class="tour-overlay" (click)="endTour()"></div>
        @if (tourTargetRect(); as rect) {
          <div class="tour-spotlight" [style.top.px]="rect.top - 8" [style.left.px]="rect.left - 8" [style.width.px]="rect.width + 16" [style.height.px]="rect.height + 16"></div>
          <div class="tour-card" [style.top.px]="rect.bottom + 16" [style.left.px]="rect.left">
            <div class="tour-step">Step {{ tourStep() + 1 }} of {{ tourSteps.length }}</div>
            <h3>{{ tourSteps[tourStep()].title }}</h3>
            <p>{{ tourSteps[tourStep()].body }}</p>
            <div class="tour-actions">
              <button class="tour-skip" (click)="endTour()">Skip tour</button>
              <button class="tour-next" (click)="nextTour()">
                {{ tourStep() === tourSteps.length - 1 ? 'Got it' : 'Next' }}
              </button>
            </div>
          </div>
        } @else {
          <!-- Target not yet in DOM — show a centered card so user can always proceed. -->
          <div class="tour-card tour-card-center">
            <div class="tour-step">Step {{ tourStep() + 1 }} of {{ tourSteps.length }}</div>
            <h3>{{ tourSteps[tourStep()].title }}</h3>
            <p>{{ tourSteps[tourStep()].body }}</p>
            <div class="tour-actions">
              <button class="tour-skip" (click)="endTour()">Skip tour</button>
              <button class="tour-next" (click)="nextTour()">
                {{ tourStep() === tourSteps.length - 1 ? 'Got it' : 'Next' }}
              </button>
            </div>
          </div>
        }
      }

      <!-- Dashboard Footer -->
      <footer class="dash-footer">
        © 2026 Copyright Reserved | A product of <a href="https://patienceai.in" target="_blank" rel="noopener" class="footer-link">Patience AI</a>
      </footer>
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
      font-size: 28px !important;
      width: 28px !important;
      height: 28px !important;
      line-height: 1;
      display: inline-flex;
      align-items: center;
      justify-content: center;
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
      right: 48px;
      top: 50%;
      transform: translateY(-50%);
      background: none;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      display: flex;
      padding: 4px;
      border-radius: 50%;
    }
    .search-clear:hover { background: var(--bg-hover); color: var(--text-primary); }
    .search-clear mat-icon { font-size: 20px; width: 20px; height: 20px; }
    
    .search-submit-btn {
      position: absolute !important;
      right: 4px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--accent) !important;
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

    /* ===== First-time tour ===== */
    .tour-overlay {
      position: fixed; inset: 0;
      background: rgba(15,23,42,0.65);
      z-index: 1500;
      animation: tourFade .2s ease;
    }
    @keyframes tourFade { from { opacity: 0; } to { opacity: 1; } }
    .tour-spotlight {
      position: fixed; z-index: 1501;
      border-radius: 12px;
      box-shadow:
        0 0 0 4px rgba(96,165,250,0.7),
        0 0 0 9999px rgba(15,23,42,0.55),
        0 0 40px 4px rgba(96,165,250,0.45);
      pointer-events: none;
      transition: top .25s ease, left .25s ease, width .25s ease, height .25s ease;
      animation: tourPulse 1.6s ease-in-out infinite;
    }
    @keyframes tourPulse {
      0%, 100% { box-shadow: 0 0 0 4px rgba(96,165,250,0.7), 0 0 0 9999px rgba(15,23,42,0.55), 0 0 30px 2px rgba(96,165,250,0.3); }
      50%       { box-shadow: 0 0 0 6px rgba(96,165,250,0.9), 0 0 0 9999px rgba(15,23,42,0.55), 0 0 60px 8px rgba(96,165,250,0.6); }
    }
    .tour-card {
      position: fixed; z-index: 1502;
      max-width: 360px;
      background: var(--surface, #ffffff);
      color: var(--text-primary, #0f172a);
      border-radius: 12px;
      padding: 16px 18px;
      box-shadow: 0 12px 40px rgba(15,23,42,0.4);
      border: 1px solid rgba(96,165,250,0.4);
      animation: tourCardIn .25s ease;
    }
    @keyframes tourCardIn { from { opacity:0; transform: translateY(10px); } to { opacity:1; transform: translateY(0); } }
    .tour-step { font-size: 11px; color: #60a5fa; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
    .tour-card h3 { margin: 6px 0 8px; font-size: 16px; font-weight: 700; }
    .tour-card p { margin: 0 0 14px; font-size: 13px; color: var(--text-secondary, #475569); line-height: 1.5; }
    .tour-actions { display: flex; justify-content: space-between; gap: 12px; }
    .tour-skip {
      background: transparent; border: none; color: #94a3b8; font-size: 13px; cursor: pointer; padding: 6px 10px;
    }
    .tour-skip:hover { color: var(--text-primary); }
    .tour-next {
      background: #2563eb; color: #fff; border: none; border-radius: 8px;
      padding: 8px 16px; font-size: 13px; font-weight: 600; cursor: pointer;
    }
    .tour-next:hover { background: #1d4ed8; }
    .tour-btn { margin-left: 8px; }
    .tour-card-center {
      top: 50% !important; left: 50% !important;
      transform: translate(-50%, -50%);
    }
    /* Live-updates indicator */
    .stat-card-live .stat-label { display: inline-flex; align-items: center; gap: 8px; }
    .live-dot {
      width: 8px; height: 8px; border-radius: 50%; background: #10b981;
      box-shadow: 0 0 0 0 rgba(16,185,129,.6);
      animation: livePulse 1.6s ease-out infinite;
      display: inline-block;
    }
    @keyframes livePulse {
      0%   { box-shadow: 0 0 0 0 rgba(16,185,129,.55); }
      70%  { box-shadow: 0 0 0 8px rgba(16,185,129,0); }
      100% { box-shadow: 0 0 0 0 rgba(16,185,129,0); }
    }
    .stat-live-text { font-size: 13px !important; font-weight: 500 !important; line-height: 1.3; }
    .website-link { color: #60a5fa; font-size: 12px; text-decoration: none; border-bottom: 1px dashed currentColor; }
    .website-link:hover { color: #93c5fd; }

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
    .dash-footer {
      text-align: center;
      padding: 24px;
      font-size: 13px;
      color: var(--text-muted);
      border-top: 1px solid var(--border);
      background: var(--bg-secondary);
      margin-top: 40px;
    }
    .footer-link {
      color: var(--accent);
      text-decoration: none;
      font-weight: 500;
      transition: color 0.2s ease;
    }
    .footer-link:hover {
      text-decoration: underline;
    }
  `],
})
export class DashboardComponent implements OnInit, OnDestroy {
  private http = inject(HttpClient);
  private enrichmentBus = inject(EnrichmentBusService);
  private companyService = inject(CompanyService);
  private scraperService = inject(ScraperService);
  private exportService = inject(ExportService);
  private snack = inject(MatSnackBar);
  private dialog = inject(MatDialog);
  auth = inject(AuthService);
  theme = inject(ThemeService);

  // Column sets switch based on the active segment.
  private companyColumns = ['company_name', 'cin', 'company_status', 'company_category', 'state', 'date_of_incorporation', 'authorised_capital', 'paid_up_capital'];
  private startupColumns = ['company_name', 'industry', 'state', 'city', 'contact_email', 'contact_phone', 'dpiit'];
  get displayedColumns(): string[] {
    return this.startupFilter === 'startups' ? this.startupColumns : this.companyColumns;
  }

  // Per-row hydrated startup detail cache, keyed by CIN.
  private _startupCache = new Map<string, any>();
  private _startupInFlight = new Set<string>();
  startupInfo(c: any): any | null {
    if (!c?.is_startup || !c?.cin || !c.cin.startsWith('SIH-')) return null;
    const cached = this._startupCache.get(c.cin);
    if (cached) return cached;
    if (!this._startupInFlight.has(c.cin)) {
      this._startupInFlight.add(c.cin);
      this.http.get<any>(`${environment.apiUrl}/startups/by-cin/${encodeURIComponent(c.cin)}`).subscribe({
        next: (v) => { this._startupCache.set(c.cin, v); this._startupInFlight.delete(c.cin); },
        error: () => { this._startupInFlight.delete(c.cin); },
      });
    }
    return null;
  }

  companies = signal<Company[]>([]);
  total = signal(0);
  stats = signal<CompanyStats | null>(null);
  loading = signal(false);
  scraping = signal(false);
  currentJob = signal<ScrapeJob | null>(null);
  exportHistory = signal<ExportHistory[]>([]);
  topStates = signal<string[]>([]);
  allStates = signal<string[]>([]);
  allCities = signal<string[]>([]);

  filter: CompanyFilter = {
    page: 1,
    pageSize: 25,
    state: undefined,
    city: undefined,
    isStartup: true,
  };

  searchValue = '';
  startupFilter: 'companies' | 'startups' = 'startups';
  filtersOpen = false;

  private searchSubject = new Subject<string>();
  private pollInterval: ReturnType<typeof setInterval> | null = null;
  private statsPollInterval: ReturnType<typeof setInterval> | null = null;
  private tablePollInterval: ReturnType<typeof setInterval> | null = null;
  private searchRecheckTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.loadData();
    this.loadStats();
    this.loadExportHistory();
    this.startStatsAutoRefresh();
    this.startTableAutoRefresh();
    this.loadStates();

    // Live-update table rows when the detail modal completes enrichment.
    this.enrichmentBus.enriched().subscribe(({ cin, data }) => {
      this._startupCache.set(cin, data);
      // Refresh the rows() signal so Angular re-renders cells using the new cache.
      this.companies.set([...this.companies()]);
    });
    // First-visit tutorial
    if (typeof window !== 'undefined' && !localStorage.getItem('tour_seen_v1')) {
      setTimeout(() => this.startTour(), 800);
    }
  }

  loadStates(): void {
    this.companyService.getStates().subscribe({
      next: (r) => this.allStates.set(r.states || []),
      error: () => {},
    });
  }

  loadCities(state: string): void {
    this.companyService.getCities(state).subscribe({
      next: (r) => this.allCities.set(r.cities || []),
      error: () => this.allCities.set([]),
    });
  }

  onCityChange(): void {
    this.filter.page = 1;
    this.loadData();
  }

  // ---- Tour ----
  tourOpen = signal(false);
  tourStep = signal(0);
  tourSteps: { selector: string; title: string; body: string; needsFilters?: boolean }[] = [
    { selector: '[data-tour="search-box"]', title: 'Search any company or startup', body: 'Type a name and press Enter. If it\'s not in our directory yet, we\'ll fetch it from Startup India and pull contact details automatically.' },
    { selector: '[data-tour="filter-toggle"]', title: 'Advanced filters', body: 'Open this to filter by state and city, or to switch between companies and startups.' },
    { selector: '[data-tour="segmented-type"]', title: 'Choose what to see', body: 'Companies shows registry data. Startups shows the Startup India directory. Searching while on Startups also live-fetches new names.', needsFilters: true },
    { selector: '[data-tour="filter-state"]', title: 'State', body: 'Pick a state to narrow the list.', needsFilters: true },
    { selector: '[data-tour="filter-city"]', title: 'City', body: 'Pick a state first; cities populate based on what we have for that state.', needsFilters: true },
    { selector: '[data-tour="stats-startups"]', title: 'Live count', body: 'This refreshes automatically as new startups are added to your directory.' },
  ];

  private _filtersOpenBeforeTour = false;

  startTour(): void {
    this._filtersOpenBeforeTour = this.filtersOpen;
    this.tourStep.set(0);
    this.tourOpen.set(true);
    this._applyStepSideEffects();
  }

  nextTour(): void {
    const next = this.tourStep() + 1;
    if (next >= this.tourSteps.length) {
      this.endTour();
    } else {
      this.tourStep.set(next);
      this._applyStepSideEffects();
    }
  }

  endTour(): void {
    this.tourOpen.set(false);
    // Restore the panel state the user had before the tour started.
    this.filtersOpen = this._filtersOpenBeforeTour;
    try { localStorage.setItem('tour_seen_v1', '1'); } catch {}
  }

  private _applyStepSideEffects(): void {
    const step = this.tourSteps[this.tourStep()];
    if (!step) return;
    if (step.needsFilters && !this.filtersOpen) {
      this.filtersOpen = true;
    }
  }

  tourTargetRect(): DOMRect | null {
    if (!this.tourOpen()) return null;
    const sel = this.tourSteps[this.tourStep()]?.selector;
    if (!sel) return null;
    const el = document.querySelector(sel) as HTMLElement | null;
    if (!el) return null;
    const r = el.getBoundingClientRect();
    // Treat zero-size / off-screen elements as missing (Angular hasn't rendered yet).
    if (r.width === 0 && r.height === 0) return null;
    el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    return r;
  }

  executeSearch(): void {
    this.filter.search = this.searchValue || undefined;
    this.filter.page = 1;
    const term = (this.searchValue || '').trim();
    const wasStartupSearch = this.startupFilter === 'startups' && !!term;
    this.loadData();

    if (!wasStartupSearch) return;

    // After the initial DB-only search settles, if it found nothing,
    // kick off the live Startup India lookup.
    setTimeout(() => {
      if (this.total() === 0 && (this.searchValue || '').trim() === term) {
        this.runStartupLookup(term);
      }
    }, 400);
  }

  private runStartupLookup(name: string): void {
    this.snack.open(`Checking Startup India for "${name}"…`, undefined, { duration: 8000 });
    this.companyService.lookupStartup(name).subscribe({
      next: (res) => {
        if (this.searchValue !== name) return; // user moved on
        if (res.status === 'found' || res.status === 'cached') {
          // The state filter on the dashboard locks to Maharashtra by default,
          // which would hide any startup from another state. Drop it for the
          // name-based reveal so the user actually sees their result.
          this.filter.state = undefined;
          this.loadData();
          this.loadStats();
          this.snack.open(`Found "${name}" on Startup India — added to your list.`, 'Close', { duration: 4000 });
        } else if (res.status === 'not_found') {
          this.dialog.open(ConfirmDialogComponent, {
            width: '440px',
            data: {
              title: 'Not on Startup India',
              message: `We checked the Startup India directory and "${name}" isn't listed there. Please double-check the name or try a different spelling.`,
              confirmText: 'OK',
              cancelText: '',
              icon: 'info',
              variant: 'primary',
            },
          });
        } else {
          // 'unavailable' — likely transient network/source issue
          const waitSeconds = 30;
          this.dialog.open(ConfirmDialogComponent, {
            width: '440px',
            data: {
              title: 'Hang tight',
              message: `We're fetching "${name}" for you. Please check back in about ${waitSeconds} seconds — we'll have the details ready.`,
              confirmText: 'OK',
              cancelText: '',
              icon: 'info',
              variant: 'primary',
            },
          });
          if (this.searchRecheckTimer) clearTimeout(this.searchRecheckTimer);
          this.searchRecheckTimer = setTimeout(() => {
            this.searchRecheckTimer = null;
            if ((this.searchValue || '').trim() === name) {
              this.runStartupLookup(name);
            }
          }, waitSeconds * 1000);
        }
      },
      error: () => {
        // Network error — quiet retry hint.
        this.snack.open('Could not reach the directory. Please try again.', 'Close', { duration: 4000 });
      },
    });
  }

  ngOnDestroy(): void {
    if (this.pollInterval) clearInterval(this.pollInterval);
    if (this.statsPollInterval) clearInterval(this.statsPollInterval);
    if (this.tablePollInterval) clearInterval(this.tablePollInterval);
    if (this.searchRecheckTimer) clearTimeout(this.searchRecheckTimer);
  }

  private startStatsAutoRefresh(): void {
    if (this.statsPollInterval) return;
    this.statsPollInterval = setInterval(() => this.loadStats(), 30000);
  }

  private startTableAutoRefresh(): void {
    if (this.tablePollInterval) return;
    this.tablePollInterval = setInterval(() => this.quietRefresh(), 30000);
  }

  /** Refetch current page + invalidate row-detail cache so columns repaint
   *  with the latest enriched data — no spinner, no jump. */
  private quietRefresh(): void {
    // Pause if the user is mid-typing in the search box.
    const active = document.activeElement as HTMLElement | null;
    if (active && active.tagName === 'INPUT' && active.classList.contains('search-input')) return;

    this.companyService.getCompanies(this.filter).subscribe({
      next: (res) => {
        // Detect any change in the rows so we only repaint when needed.
        const fresh = res.items || [];
        const current = this.companies();
        let changed = fresh.length !== current.length;
        if (!changed) {
          for (let i = 0; i < fresh.length; i++) {
            if (current[i]?.id !== fresh[i]?.id) { changed = true; break; }
          }
        }
        // Always trim the cache to current page CINs so we re-hydrate fresh data.
        this._startupCache.clear();
        if (changed || res.total !== this.total()) {
          this.companies.set(fresh);
          this.total.set(res.total);
        } else {
          // Same rows; still nudge the signal so the table reads the cleared cache.
          this.companies.set([...current]);
        }
      },
      error: () => { /* silent */ },
    });
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
    // Companies view is currently limited to Maharashtra coverage.
    if (this.startupFilter === 'companies'
        && this.filter.state
        && this.filter.state.trim().toLowerCase() !== 'maharashtra') {
      const tried = this.filter.state;
      setTimeout(() => { this.filter.state = 'Maharashtra'; this.filter.city = undefined; this.allCities.set([]); });
      this.dialog.open(ConfirmDialogComponent, {
        width: '440px',
        data: {
          title: 'Coming soon',
          message: `Company data for ${tried} is on our roadmap — we'll have it ready shortly. For now company coverage is limited to Maharashtra. Switch to the Startups view to explore ${tried} now.`,
          confirmText: 'Got it',
          cancelText: '',
          icon: 'info',
          variant: 'primary',
        },
      });
      return;
    }
    this.filter.city = undefined;
    this.allCities.set([]);
    if (this.filter.state) this.loadCities(this.filter.state);
    this.filter.page = 1;
    this.loadData();
  }



  onPage(e: PageEvent): void {
    this.filter.page = e.pageIndex + 1;
    this.filter.pageSize = e.pageSize;
    this.loadData();
  }

  clearSearch(): void {
    this.searchValue = '';
    this.executeSearch();
  }

  resetFilters(): void {
    this.searchValue = '';
    this.startupFilter = 'startups';
    this.filter = {
      page: 1,
      pageSize: 25,
      state: undefined,
      city: undefined,
      isStartup: true,
    };
    this.allCities.set([]);
    this.loadData();
  }

  setStartupFilter(val: 'companies' | 'startups'): void {
    this.startupFilter = val;
    this.filter.isStartup = val === 'startups';
    if (val === 'companies') {
      // Companies view is Maharashtra-only — auto-apply.
      if (!this.filter.state || this.filter.state.trim().toLowerCase() !== 'maharashtra') {
        this.filter.state = 'Maharashtra';
        this.filter.city = undefined;
        this.allCities.set([]);
        this.loadCities('Maharashtra');
      }
    }
    this.filter.page = 1;
    this.loadData();
  }

  activeFilterCount(): number {
    let n = 0;
    if (this.searchValue) n++;
    if (this.filter.state) n++;
    if (this.filter.city) n++;
    return n;
  }

  triggerScrape(): void {
    this.scraperService.trigger(undefined, undefined).subscribe({
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
    this.exportService.export(type, undefined, undefined, this.filter.state, this.filter.isStartup).subscribe({
      next: (res) => {
        window.open(res.download_url, '_blank');
        this.loadExportHistory();
      },
      error: () => this.snack.open('Export failed', 'Close', { duration: 3000 }),
    });
  }

  openCompanyDialog(c: Company): void {
    // All startup rows use the richer Startup India profile dialog.
    if (c.is_startup) {
      this.dialog.open(StartupDetailDialogComponent, {
        data: {
          cin: c.cin || null,
          companyName: c.company_name,
          fallback: {
            state: c.state,
            company_status: c.company_status,
            company_category: c.company_category,
            date_of_incorporation: c.date_of_incorporation,
            website: c.website,
            match_method: c.match_method,
          },
        },
        panelClass: 'startup-detail-panel',
        width: '760px',
        maxWidth: '95vw',
        maxHeight: '90vh',
        autoFocus: false,
      });
      return;
    }
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
