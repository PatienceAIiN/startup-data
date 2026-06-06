import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ConsentBannerComponent } from './shared/consent-banner/consent-banner.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, ConsentBannerComponent],
  template: `
    <router-outlet />
    <app-consent-banner />
  `,
})
export class AppComponent {}
