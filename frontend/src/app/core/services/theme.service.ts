import { Injectable, signal, effect } from '@angular/core';

export type ThemeMode = 'dark' | 'light';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly STORAGE_KEY = 'si-theme';
  theme = signal<ThemeMode>(this._loadInitial());

  constructor() {
    effect(() => {
      const t = this.theme();
      document.body.classList.remove('theme-dark', 'theme-light');
      document.body.classList.add(`theme-${t}`);
      localStorage.setItem(this.STORAGE_KEY, t);
    });
  }

  toggle(): void {
    this.theme.set(this.theme() === 'dark' ? 'light' : 'dark');
  }

  private _loadInitial(): ThemeMode {
    const saved = localStorage.getItem(this.STORAGE_KEY) as ThemeMode | null;
    return saved === 'dark' ? 'dark' : 'light';
  }
}
