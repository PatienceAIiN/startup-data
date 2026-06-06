import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthTokens, User } from '../models/user.model';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  private apiUrl = `${environment.apiUrl}/auth`;

  currentUser = signal<User | null>(this._loadUser());

  constructor() {
    // When the browser restores this tab from the bfcache (back/forward
    // navigation), check whether the user is still authenticated. If they
    // logged out in another tab — or if the stale page is showing a
    // protected route — force a reload so the auth guard kicks in.
    if (typeof window !== 'undefined') {
      window.addEventListener('pageshow', (e: PageTransitionEvent) => {
        if (e.persisted && !this.isAuthenticated()) {
          window.location.replace('/');
        }
      });
    }
  }

  private _loadUser(): User | null {
    const u = localStorage.getItem('user');
    return u ? JSON.parse(u) : null;
  }

  login(email: string, password: string): Observable<AuthTokens> {
    return this.http.post<AuthTokens>(`${this.apiUrl}/login`, { email, password }).pipe(
      tap(res => this._saveAuth(res))
    );
  }

  signup(email: string, password: string, fullName: string): Observable<AuthTokens> {
    return this.http.post<AuthTokens>(`${this.apiUrl}/signup`, {
      email, password, full_name: fullName
    }).pipe(tap(res => this._saveAuth(res)));
  }

  logout(): void {
    // Wipe every trace of the session.
    try {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      // Defensive: clear anything else the app may have stashed.
      sessionStorage.clear();
    } catch {}
    this.currentUser.set(null);
    // Hard navigation + history replace — the browser back button can't
    // return to /dashboard because that history entry is overwritten, and a
    // full page load drops all in-memory Angular state (caches, signals,
    // pending HTTP requests, etc.) so nothing leaks across sessions.
    try {
      window.location.replace('/');
    } catch {
      // Fallback for any non-browser context (SSR/tests).
      this.router.navigate(['/'], { replaceUrl: true });
    }
  }

  getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  isAdmin(): boolean {
    return this.currentUser()?.is_admin ?? false;
  }

  private _saveAuth(res: AuthTokens): void {
    localStorage.setItem('access_token', res.access_token);
    localStorage.setItem('refresh_token', res.refresh_token);
    localStorage.setItem('user', JSON.stringify(res.user));
    this.currentUser.set(res.user);
  }
}
