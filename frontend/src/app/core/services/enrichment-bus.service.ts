import { Injectable } from '@angular/core';
import { Subject, Observable } from 'rxjs';

/** Cross-component bus so when scraper-2 completes inside the detail modal,
 *  the dashboard table can refresh that row in place. */
@Injectable({ providedIn: 'root' })
export class EnrichmentBusService {
  private _enriched$ = new Subject<{ cin: string; data: any }>();

  enriched(): Observable<{ cin: string; data: any }> {
    return this._enriched$.asObservable();
  }

  notify(cin: string, data: any): void {
    this._enriched$.next({ cin, data });
  }
}
