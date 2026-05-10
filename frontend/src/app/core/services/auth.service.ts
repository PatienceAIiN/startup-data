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
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    this.currentUser.set(null);
    this.router.navigate(['/login']);
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
