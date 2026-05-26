import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    title: 'Nexus Company Intel | B2B Intelligence & Market Insights',
    loadComponent: () => import('./features/landing/landing.component').then(m => m.LandingComponent),
  },
  {
    path: 'login',
    title: 'Nexus Company Intel | Login',
    loadComponent: () => import('./features/auth/login/login.component').then(m => m.LoginComponent),
  },
  {
    path: 'signup',
    title: 'Nexus Company Intel | Signup',
    loadComponent: () => import('./features/auth/signup/signup.component').then(m => m.SignupComponent),
  },
  {
    path: 'dashboard',
    title: 'Nexus Company Intel | Dashboard',
    canActivate: [authGuard],
    loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
  },
  {
    path: 'companies',
    title: 'Nexus Company Intel | Companies',
    canActivate: [authGuard],
    loadComponent: () => import('./features/companies/company-list/company-list.component').then(m => m.CompanyListComponent),
  },
  {
    path: 'companies/:id',
    title: 'Nexus Company Intel | Company Detail',
    canActivate: [authGuard],
    loadComponent: () => import('./features/companies/company-detail/company-detail.component').then(m => m.CompanyDetailComponent),
  },
  { path: '**', redirectTo: '/dashboard' },
];
