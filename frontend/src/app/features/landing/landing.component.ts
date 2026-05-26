import { Component, inject, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-landing',
  standalone: true,
  encapsulation: ViewEncapsulation.None,
  imports: [CommonModule, RouterLink, MatButtonModule, MatIconModule],
  template: `
    <div class="landing-page">
      <!-- Background glow effects -->
      <div class="ambient-glow glow-1"></div>
      <div class="ambient-glow glow-2"></div>

      <!-- Navigation Header -->
      <header class="landing-header">
        <div class="landing-logo">
          <mat-icon class="logo-icon-pulse">hub</mat-icon>
          <span class="logo-text">Nexus Company</span>
        @if (auth.isAuthenticated()) {
          <div class="landing-nav-actions">
            <a mat-flat-button routerLink="/dashboard" class="nav-enter-btn">
              <span>Go to Dashboard</span>
              <mat-icon>arrow_forward</mat-icon>
            </a>
          </div>
        }
      </header>

      <!-- Main Hero Content -->
      <main class="landing-hero">
        <div class="hero-capsule">
          <span class="capsule-text">Enterprise B2B Intelligence</span>
        </div>

        <h1 class="hero-title">
          <span>Identify.</span>
          <span>Analyze.</span>
          <span>Scale.</span>
        </h1>

        <p class="hero-subtitle">
          The premier corporate directory and private startup map designed for modern investment research, private equity, and enterprise growth teams.
        </p>

        <!-- Centered Premium Action Buttons -->
        <div class="hero-actions">
          @if (auth.isAuthenticated()) {
            <a mat-flat-button routerLink="/dashboard" class="hero-btn-primary enter-dashboard">
              <span>Enter Workspace</span>
              <mat-icon>explore</mat-icon>
            </a>
          } @else {
            <a mat-flat-button routerLink="/login" class="hero-btn-primary">
              <span>Sign In</span>
              <mat-icon>login</mat-icon>
            </a>
            <a mat-stroked-button routerLink="/signup" class="hero-btn-secondary">
              <span>Create Account</span>
              <mat-icon>how_to_reg</mat-icon>
            </a>
          }
        </div>
      </main>

      <!-- Minimalist Footer -->
      <footer class="landing-footer">
        © 2026 Copyright Reserved | A product of <a href="https://patienceai.in" target="_blank" rel="noopener" class="footer-link">Patience AI</a>
      </footer>
    </div>
  `,
  styles: [`
    .landing-page {
      min-height: 100vh;
      background: #020617;
      color: #f1f5f9;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      position: relative;
      overflow: hidden;
      font-family: 'Inter', Roboto, sans-serif;
    }

    /* Ambient Tesla-style moving glow circles */
    .ambient-glow {
      position: absolute;
      border-radius: 50%;
      filter: blur(100px);
      z-index: 0;
      opacity: 0.15;
      pointer-events: none;
    }
    .glow-1 {
      background: #10b981;
      width: 500px;
      height: 500px;
      top: -150px;
      left: -100px;
      animation: teslaBg 18s ease-in-out infinite alternate;
    }
    .glow-2 {
      background: #3b82f6;
      width: 600px;
      height: 600px;
      bottom: -200px;
      right: -100px;
      animation: teslaBg 22s ease-in-out infinite alternate-reverse;
    }

    @keyframes teslaBg {
      0% {
        transform: translate(0, 0) scale(1);
        opacity: 0.12;
      }
      50% {
        transform: translate(60px, -40px) scale(1.1);
        opacity: 0.18;
      }
      100% {
        transform: translate(-40px, 80px) scale(0.95);
        opacity: 0.12;
      }
    }

    /* Header Nav */
    .landing-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 32px 64px;
      position: relative;
      z-index: 10;
      animation: teslaFadeIn 1s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
    @media (max-width: 640px) {
      .landing-header {
        padding: 24px;
      }
    }
    .landing-logo {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .logo-icon-pulse {
      color: #34d399 !important;
      font-size: 28px !important;
      width: 28px !important;
      height: 28px !important;
      filter: drop-shadow(0 0 10px rgba(52, 211, 153, 0.3));
    }
    .logo-text {
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.5px;
      background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .landing-nav-actions {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .nav-login-btn {
      color: #94a3b8 !important;
      font-weight: 600 !important;
      font-size: 14px !important;
    }
    .nav-login-btn:hover {
      color: #ffffff !important;
    }
    .nav-signup-btn, .nav-enter-btn {
      background: rgba(255, 255, 255, 0.08) !important;
      border: 1px solid rgba(255, 255, 255, 0.1) !important;
      color: #ffffff !important;
      border-radius: 8px !important;
      font-size: 14px !important;
      font-weight: 600 !important;
      height: 40px !important;
      padding: 0 18px !important;
      transition: all 0.3s ease !important;
    }
    .nav-signup-btn:hover, .nav-enter-btn:hover {
      background: #ffffff !important;
      color: #020617 !important;
      box-shadow: 0 4px 20px rgba(255, 255, 255, 0.15);
    }
    .nav-enter-btn mat-icon {
      font-size: 16px !important;
      width: 16px !important;
      height: 16px !important;
      margin-left: 6px;
    }

    /* Hero Centered Section */
    .landing-hero {
      max-width: 800px;
      margin: 0 auto;
      text-align: center;
      padding: 40px 24px;
      position: relative;
      z-index: 10;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .hero-capsule {
      background: rgba(52, 211, 153, 0.08);
      border: 1px solid rgba(52, 211, 153, 0.2);
      border-radius: 30px;
      padding: 6px 16px;
      margin-bottom: 32px;
      display: inline-flex;
      animation: teslaFadeIn 1s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      animation-delay: 0.1s;
      opacity: 0;
    }
    .capsule-text {
      color: #34d399;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
    }

    .hero-title {
      font-size: 80px;
      font-weight: 900;
      line-height: 1.05;
      letter-spacing: -2px;
      margin: 0 0 24px;
      display: flex;
      flex-direction: column;
      animation: teslaFadeIn 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      animation-delay: 0.2s;
      opacity: 0;
    }
    @media (max-width: 640px) {
      .hero-title {
        font-size: 48px;
        letter-spacing: -1px;
      }
    }
    .hero-title span:nth-child(1) {
      background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .hero-title span:nth-child(2) {
      background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .hero-title span:nth-child(3) {
      background: linear-gradient(135deg, #34d399 0%, #10b981 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .hero-subtitle {
      font-size: 18px;
      line-height: 1.6;
      color: #94a3b8;
      max-width: 600px;
      margin: 0 auto 40px;
      font-weight: 400;
      animation: teslaFadeIn 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      animation-delay: 0.3s;
      opacity: 0;
    }
    @media (max-width: 640px) {
      .hero-subtitle {
        font-size: 15px;
      }
    }

    .hero-actions {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 20px;
      width: 100%;
      max-width: 480px;
      animation: teslaFadeIn 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      animation-delay: 0.4s;
      opacity: 0;
    }
    @media (max-width: 480px) {
      .hero-actions {
        flex-direction: column;
        gap: 12px;
      }
      .hero-btn-primary, .hero-btn-secondary {
        width: 100% !important;
      }
    }

    .hero-btn-primary {
      background: #10b981 !important;
      color: #ffffff !important;
      font-size: 15px !important;
      font-weight: 600 !important;
      height: 52px !important;
      padding: 0 32px !important;
      border-radius: 10px !important;
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
      box-shadow: 0 4px 20px rgba(16, 185, 129, 0.2) !important;
      transition: all 0.3s ease !important;
    }
    .hero-btn-primary:hover {
      background: #059669 !important;
      transform: translateY(-2px);
      box-shadow: 0 8px 30px rgba(5, 150, 105, 0.3) !important;
    }
    .hero-btn-primary mat-icon {
      font-size: 20px !important;
      width: 20px !important;
      height: 20px !important;
      margin-left: 8px;
    }

    .hero-btn-secondary {
      border: 1.5px solid rgba(255, 255, 255, 0.15) !important;
      background: rgba(255, 255, 255, 0.03) !important;
      color: #ffffff !important;
      font-size: 15px !important;
      font-weight: 600 !important;
      height: 52px !important;
      padding: 0 32px !important;
      border-radius: 10px !important;
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
      transition: all 0.3s ease !important;
      backdrop-filter: blur(10px);
    }
    .hero-btn-secondary:hover {
      background: rgba(255, 255, 255, 0.08) !important;
      border-color: rgba(255, 255, 255, 0.3) !important;
      transform: translateY(-2px);
    }
    .hero-btn-secondary mat-icon {
      font-size: 20px !important;
      width: 20px !important;
      height: 20px !important;
      margin-left: 8px;
    }

    /* Light Theme Styling for Landing Page */
    body.theme-light .landing-page {
      background: #f8fafc;
      color: #0f172a;
    }
    body.theme-light .logo-text {
      background: linear-gradient(135deg, #0f172a 0%, #334155 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    body.theme-light .logo-icon-pulse {
      color: #059669 !important;
    }
    body.theme-light .nav-login-btn {
      color: #475569 !important;
    }
    body.theme-light .nav-login-btn:hover {
      color: #0f172a !important;
    }
    body.theme-light .nav-signup-btn, body.theme-light .nav-enter-btn {
      background: rgba(15, 23, 42, 0.04) !important;
      border: 1px solid rgba(15, 23, 42, 0.08) !important;
      color: #0f172a !important;
    }
    body.theme-light .nav-signup-btn:hover, body.theme-light .nav-enter-btn:hover {
      background: #0f172a !important;
      color: #ffffff !important;
    }
    body.theme-light .hero-title span:nth-child(1) {
      background: linear-gradient(135deg, #0f172a 0%, #334155 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    body.theme-light .hero-title span:nth-child(2) {
      background: linear-gradient(135deg, #64748b 0%, #475569 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    body.theme-light .hero-title span:nth-child(3) {
      background: linear-gradient(135deg, #059669 0%, #047857 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    body.theme-light .hero-subtitle {
      color: #475569;
    }
    body.theme-light .hero-btn-primary {
      background: #059669 !important;
    }
    body.theme-light .hero-btn-primary:hover {
      background: #047857 !important;
    }
    body.theme-light .hero-btn-secondary {
      border: 1.5px solid rgba(15, 23, 42, 0.15) !important;
      background: rgba(15, 23, 42, 0.02) !important;
      color: #0f172a !important;
    }
    body.theme-light .hero-btn-secondary:hover {
      background: rgba(15, 23, 42, 0.06) !important;
    }
    body.theme-light .landing-footer {
      color: #64748b !important;
      border-top: 1px solid rgba(15, 23, 42, 0.08) !important;
    }
    body.theme-light .footer-link {
      color: #059669 !important;
    }
    body.theme-light .footer-link:hover {
      color: #2563eb !important;
    }

    /* Footer */
    .landing-footer {
      text-align: center;
      padding: 32px;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.4);
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      position: relative;
      z-index: 10;
    }
    .footer-link {
      color: #34d399;
      text-decoration: none;
      font-weight: 500;
      transition: color 0.2s ease;
    }
    .footer-link:hover {
      color: #60a5fa;
      text-decoration: underline;
    }
  `],
})
export class LandingComponent {
  auth = inject(AuthService);
}
