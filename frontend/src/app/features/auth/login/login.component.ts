import { Component, inject, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink, ActivatedRoute } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  encapsulation: ViewEncapsulation.None,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    MatFormFieldModule, MatInputModule, MatButtonModule,
    MatSnackBarModule, MatProgressSpinnerModule, MatIconModule,
  ],
  template: `
    <div class="auth-page">
      <div class="auth-card">
        <!-- Header -->
        <div class="auth-header">
          <div class="auth-logo">🚀</div>
          <h1 class="auth-title">StartupIntel</h1>
          <p class="auth-subtitle">India's B2B Intelligence Platform</p>
        </div>

        <!-- Form -->
        <form [formGroup]="form" (ngSubmit)="onSubmit()" class="auth-form">

          <mat-form-field appearance="outline" class="auth-field">
            <mat-label>Email Address</mat-label>
            <mat-icon matPrefix>email</mat-icon>
            <input matInput type="email" formControlName="email" placeholder="you@company.com" autocomplete="email" />
            @if (form.get('email')?.invalid && form.get('email')?.touched) {
              <mat-error>Please enter a valid email</mat-error>
            }
          </mat-form-field>

          <mat-form-field appearance="outline" class="auth-field">
            <mat-label>Password</mat-label>
            <mat-icon matPrefix>lock</mat-icon>
            <input matInput [type]="showPassword ? 'text' : 'password'" formControlName="password" autocomplete="current-password" />
            <button mat-icon-button matSuffix type="button" (click)="showPassword = !showPassword">
              <mat-icon>{{ showPassword ? 'visibility_off' : 'visibility' }}</mat-icon>
            </button>
            @if (form.get('password')?.invalid && form.get('password')?.touched) {
              <mat-error>Password is required</mat-error>
            }
          </mat-form-field>

          <button
            mat-flat-button
            type="submit"
            class="auth-submit-btn"
            [disabled]="loading || form.invalid"
          >
            @if (loading) {
              <mat-spinner diameter="20" class="btn-spinner"></mat-spinner>
            } @else {
              <mat-icon>login</mat-icon>
            }
            {{ loading ? 'Signing in...' : 'Sign In' }}
          </button>
        </form>

        <div class="auth-footer">
          <span>Don't have an account?</span>
          <a routerLink="/signup" class="auth-link">Create account</a>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .auth-page {
      min-height: 100vh;
      background: #0f172a;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }
    .auth-card {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 16px;
      padding: 40px;
      width: 100%;
      max-width: 420px;
      box-shadow: 0 25px 50px rgba(0,0,0,0.5);
    }
    .auth-header {
      text-align: center;
      margin-bottom: 32px;
    }
    .auth-logo {
      font-size: 48px;
      margin-bottom: 12px;
      line-height: 1;
    }
    .auth-title {
      font-size: 28px;
      font-weight: 700;
      color: #34d399;
      margin: 0 0 6px;
    }
    .auth-subtitle {
      color: #64748b;
      margin: 0;
      font-size: 14px;
    }
    .auth-form {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .auth-field {
      width: 100%;
    }
    /* Material form field dark overrides */
    .auth-field .mdc-text-field--outlined:not(.mdc-text-field--disabled) {
      background: rgba(15, 23, 42, 0.5) !important;
    }
    .auth-field .mdc-notched-outline__leading,
    .auth-field .mdc-notched-outline__notch,
    .auth-field .mdc-notched-outline__trailing {
      border-color: #475569 !important;
    }
    .auth-field:hover .mdc-notched-outline__leading,
    .auth-field:hover .mdc-notched-outline__notch,
    .auth-field:hover .mdc-notched-outline__trailing {
      border-color: #94a3b8 !important;
    }
    .auth-field.mat-focused .mdc-notched-outline__leading,
    .auth-field.mat-focused .mdc-notched-outline__notch,
    .auth-field.mat-focused .mdc-notched-outline__trailing {
      border-color: #34d399 !important;
      border-width: 2px !important;
    }
    .auth-field .mdc-floating-label {
      color: #64748b !important;
    }
    .auth-field.mat-focused .mdc-floating-label {
      color: #34d399 !important;
    }
    .auth-field input.mat-mdc-input-element {
      color: #f1f5f9 !important;
    }
    .auth-field .mat-mdc-form-field-icon-prefix mat-icon,
    .auth-field .mat-mdc-form-field-icon-suffix mat-icon {
      color: #64748b;
    }
    .auth-field.mat-focused .mat-mdc-form-field-icon-prefix mat-icon {
      color: #34d399;
    }
    .auth-submit-btn {
      margin-top: 8px;
      width: 100%;
      height: 48px;
      background: #10b981 !important;
      color: #fff !important;
      font-size: 15px;
      font-weight: 600;
      border-radius: 8px !important;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }
    .auth-submit-btn:disabled {
      background: #134e4a !important;
      color: #6b7280 !important;
    }
    .auth-submit-btn mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
    }
    .btn-spinner {
      display: inline-block;
    }
    .btn-spinner circle {
      stroke: #fff !important;
    }
    .auth-footer {
      text-align: center;
      margin-top: 24px;
      color: #64748b;
      font-size: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }
    .auth-link {
      color: #34d399;
      text-decoration: none;
      font-weight: 600;
    }
    .auth-link:hover {
      text-decoration: underline;
    }
  `],
})
export class LoginComponent {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private snack = inject(MatSnackBar);

  loading = false;
  showPassword = false;

  form = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', Validators.required],
  });

  onSubmit(): void {
    if (this.form.invalid) return;
    this.loading = true;
    const { email, password } = this.form.value;
    this.auth.login(email!, password!).subscribe({
      next: () => {
        const returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/dashboard';
        this.router.navigateByUrl(returnUrl);
      },
      error: (err) => {
        this.loading = false;
        const msg = err.error?.detail || 'Login failed. Check your credentials.';
        this.snack.open(msg, 'Close', { duration: 4000 });
      },
    });
  }
}
