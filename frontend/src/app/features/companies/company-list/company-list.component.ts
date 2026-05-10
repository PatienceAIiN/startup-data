import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-company-list',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="min-h-screen bg-slate-900 text-white p-6">
      <a routerLink="/dashboard" class="text-emerald-400 hover:underline">← Back to Dashboard</a>
      <h1 class="text-2xl font-bold mt-4">Company List</h1>
    </div>
  `,
})
export class CompanyListComponent {}
