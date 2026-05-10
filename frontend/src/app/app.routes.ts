import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login/login.component').then(m => m.LoginComponent),
  },
  {
    path: 'signup',
    loadComponent: () => import('./features/auth/signup/signup.component').then(m => m.SignupComponent),
  },
  {
    path: 'dashboard',
    canActivate: [authGuard],
    loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
  },
  {
    path: 'companies',
    canActivate: [authGuard],
    loadComponent: () => import('./features/companies/company-list/company-list.component').then(m => m.CompanyListComponent),
  },
  {
    path: 'companies/:id',
    canActivate: [authGuard],
    loadComponent: () => import('./features/companies/company-detail/company-detail.component').then(m => m.CompanyDetailComponent),
  },
  { path: '**', redirectTo: '/dashboard' },
];
