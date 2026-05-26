import { Component, inject, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators, AbstractControl } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { AuthService } from '../../../core/services/auth.service';

function passwordValidator(control: AbstractControl) {
  const v = control.value || '';
  if (v.length < 8) return { weak: 'At least 8 characters required' };
  if (!/[A-Z]/.test(v)) return { weak: 'Include at least one uppercase letter' };
  if (!/[0-9]/.test(v)) return { weak: 'Include at least one digit' };
  return null;
}

@Component({
  selector: 'app-signup',
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
          <h1 class="auth-title">Nexus Intel</h1>
          <p class="auth-subtitle">Create your account</p>
        </div>

        <!-- Form -->
        <form [formGroup]="form" (ngSubmit)="onSubmit()" class="auth-form">

          <mat-form-field appearance="outline" class="auth-field">
            <mat-label>Full Name</mat-label>
            <mat-icon matPrefix>person</mat-icon>
            <input matInput formControlName="fullName" autocomplete="name" />
            @if (form.get('fullName')?.invalid && form.get('fullName')?.touched) {
              <mat-error>At least 2 characters required</mat-error>
            }
          </mat-form-field>

          <mat-form-field appearance="outline" class="auth-field">
            <mat-label>Email Address</mat-label>
            <mat-icon matPrefix>email</mat-icon>
            <input matInput type="email" formControlName="email" autocomplete="email" />
            @if (form.get('email')?.invalid && form.get('email')?.touched) {
              <mat-error>Please enter a valid email</mat-error>
            }
          </mat-form-field>

          <mat-form-field appearance="outline" class="auth-field">
            <mat-label>Password</mat-label>
            <mat-icon matPrefix>lock</mat-icon>
            <input matInput [type]="showPassword ? 'text' : 'password'" formControlName="password" autocomplete="new-password" />
            <button mat-icon-button matSuffix type="button" (click)="showPassword = !showPassword">
              <mat-icon>{{ showPassword ? 'visibility_off' : 'visibility' }}</mat-icon>
            </button>
            @if (form.get('password')?.errors?.['weak']) {
              <mat-error>{{ form.get('password')?.errors?.['weak'] }}</mat-error>
            }
          </mat-form-field>

          <!-- Password strength -->
          <div class="strength-bar">
            <div class="strength-track">
              @for (i of [1,2,3,4]; track i) {
                <div class="strength-seg" [style.background]="segColor(i)"></div>
              }
            </div>
            <span class="strength-label" [style.color]="strengthLabelColor()">{{ strengthLabel() }}</span>
          </div>

          <button
            mat-flat-button
            type="submit"
            class="auth-submit-btn"
            [disabled]="loading || form.invalid"
          >
            @if (loading) {
              <mat-spinner diameter="20" class="btn-spinner"></mat-spinner>
            } @else {
              <mat-icon>how_to_reg</mat-icon>
            }
            {{ loading ? 'Creating account...' : 'Create Account' }}
          </button>
        </form>

        <div class="auth-footer">
          <span>Already have an account?</span>
          <a routerLink="/login" class="auth-link">Sign in</a>
        </div>

        <div class="product-credit">
          © 2026 Copyright Reserved | A product of <a href="https://patienceai.in" target="_blank" rel="noopener" class="credit-link">Patience AI</a>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .auth-page {
      min-height: 100vh;
      background: linear-gradient(135deg, #020617 0%, #0f172a 50%, #1e1b4b 100%);
      background-size: 200% 200%;
      animation: gradientBG 15s ease infinite;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
      position: relative;
      overflow: hidden;
    }
    @keyframes gradientBG {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }
    .auth-page::before, .auth-page::after {
      content: '';
      position: absolute;
      width: 400px;
      height: 400px;
      border-radius: 50%;
      filter: blur(80px);
      z-index: 0;
      animation: float 10s ease-in-out infinite;
    }
    .auth-page::before {
      background: rgba(16, 185, 129, 0.2);
      top: -100px;
      left: -100px;
    }
    .auth-page::after {
      background: rgba(99, 102, 241, 0.15);
      bottom: -100px;
      right: -100px;
      animation-delay: -5s;
    }
    @keyframes float {
      0%, 100% { transform: translateY(0) scale(1); }
      50% { transform: translateY(-30px) scale(1.05); }
    }
    .auth-card {
      background: rgba(30, 41, 59, 0.7);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 24px;
      padding: 48px 40px;
      width: 100%;
      max-width: 440px;
      box-shadow: 0 25px 50px -12px rgba(0,0,0,0.7);
      position: relative;
      z-index: 1;
      transform: translateY(0);
      transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .auth-card:hover {
      transform: translateY(-5px);
      box-shadow: 0 30px 60px -12px rgba(0,0,0,0.8);
    }
    .auth-header {
      text-align: center;
      margin-bottom: 32px;
    }
    .auth-logo {
      font-size: 56px;
      margin-bottom: 16px;
      line-height: 1;
      filter: drop-shadow(0 0 15px rgba(52, 211, 153, 0.4));
      animation: pulse 3s infinite;
    }
    @keyframes pulse {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.05); }
    }
    .auth-title {
      font-size: 32px;
      font-weight: 800;
      background: linear-gradient(to right, #34d399, #3b82f6);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin: 0 0 8px;
    }
    .auth-subtitle {
      color: #94a3b8;
      margin: 0;
      font-size: 15px;
    }
    .auth-form {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .auth-field {
      width: 100%;
    }
    .auth-field .mdc-text-field--outlined:not(.mdc-text-field--disabled) {
      background: rgba(15, 23, 42, 0.4) !important;
      border-bottom: 1px solid rgba(255, 255, 255, 0.15) !important;
      border-radius: 8px !important;
      transition: all 0.3s ease;
    }
    .auth-field:hover .mdc-text-field--outlined:not(.mdc-text-field--disabled) {
      background: rgba(15, 23, 42, 0.6) !important;
      border-bottom: 1px solid rgba(255, 255, 255, 0.3) !important;
    }
    .auth-field.mat-focused .mdc-text-field--outlined:not(.mdc-text-field--disabled) {
      background: rgba(15, 23, 42, 0.7) !important;
      border-bottom: 2px solid #34d399 !important;
      box-shadow: 0 4px 20px rgba(52, 211, 153, 0.15);
    }
    .auth-field .mat-mdc-form-field-subscript-wrapper {
      display: none;
    }
    .auth-field .mdc-line-ripple,
    .auth-field .mdc-line-ripple::before,
    .auth-field .mdc-line-ripple::after {
      display: none !important;
    }
    .auth-field .mat-mdc-form-field-underline,
    .auth-field .mat-mdc-form-field-ripple {
      display: none !important;
    }
    .auth-field .mdc-notched-outline__leading,
    .auth-field .mdc-notched-outline__notch,
    .auth-field .mdc-notched-outline__trailing {
      border: none !important;
    }
    .auth-field .mdc-floating-label {
      color: #94a3b8 !important;
    }
    .auth-field.mat-focused .mdc-floating-label {
      color: #34d399 !important;
    }
    .auth-field input.mat-mdc-input-element {
      color: #f1f5f9 !important;
    }
    .auth-field .mat-mdc-form-field-icon-prefix mat-icon,
    .auth-field .mat-mdc-form-field-icon-suffix mat-icon {
      color: #94a3b8;
    }
    .auth-field.mat-focused .mat-mdc-form-field-icon-prefix mat-icon {
      color: #34d399;
    }
    /* Strength bar */
    .strength-bar {
      display: flex;
      align-items: center;
      gap: 10px;
      margin: -8px 0 8px;
      padding: 0 4px;
    }
    .strength-track {
      flex: 1;
      display: flex;
      gap: 4px;
    }
    .strength-seg {
      flex: 1;
      height: 4px;
      border-radius: 2px;
      background: #334155;
      transition: background 0.3s;
    }
    .strength-label {
      font-size: 11px;
      font-weight: 600;
      min-width: 40px;
      text-align: right;
    }
    /* Submit button */
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
    .auth-submit-btn mat-icon { font-size: 20px; width: 20px; height: 20px; }
    .btn-spinner { display: inline-block; }
    .btn-spinner circle { stroke: #fff !important; }
    .auth-footer {
      text-align: center;
      margin-top: 24px;
      color: #64748b;
      font-size: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .auth-link { color: #34d399; text-decoration: none; font-weight: 600; }
    .auth-link:hover { text-decoration: underline; }
    .product-credit {
      text-align: center;
      margin-top: 24px;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.4);
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      padding-top: 16px;
    }
    .credit-link {
      color: #34d399;
      text-decoration: none;
      font-weight: 500;
      transition: color 0.2s ease;
    }
    .credit-link:hover {
      color: #60a5fa;
      text-decoration: underline;
    }
  `],
})
export class SignupComponent {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);
  private snack = inject(MatSnackBar);

  loading = false;
  showPassword = false;

  form = this.fb.group({
    fullName: ['', [Validators.required, Validators.minLength(2)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, passwordValidator]],
  });

  private _score(): number {
    const pw = this.form.get('password')?.value || '';
    let score = 0;
    if (pw.length >= 8) score++;
    if (/[A-Z]/.test(pw)) score++;
    if (/[0-9]/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;
    return score;
  }

  segColor(level: number): string {
    const score = this._score();
    if (level > score) return '#334155';
    const palette = ['#ef4444', '#f97316', '#eab308', '#22c55e'];
    return palette[score - 1] || '#334155';
  }

  strengthLabel(): string {
    const labels = ['', 'Weak', 'Fair', 'Good', 'Strong'];
    return labels[this._score()] || '';
  }

  strengthLabelColor(): string {
    const colors = ['', '#ef4444', '#f97316', '#eab308', '#22c55e'];
    return colors[this._score()] || '#64748b';
  }

  onSubmit(): void {
    if (this.form.invalid) return;
    this.loading = true;
    const { fullName, email, password } = this.form.value;
    this.auth.signup(email!, password!, fullName!).subscribe({
      next: () => this.router.navigate(['/dashboard']),
      error: (err) => {
        this.loading = false;
        const detail = err.error?.detail;
        const msg = Array.isArray(detail) ? detail[0]?.msg : (detail || 'Signup failed');
        this.snack.open(msg, 'Close', { duration: 4000 });
      },
    });
  }
}
